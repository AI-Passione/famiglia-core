import json
import os
import platform
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging
import yaml

from famiglia_core.command_center.backend.github.auth_github import github_oauth_client
from famiglia_core.command_center.backend.notion.auth_notion import notion_oauth_client
from famiglia_core.command_center.backend.slack.auth_slack import slack_oauth_client
from famiglia_core.db.tools.user_connections_store import user_connections_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "docker-compose.yml").exists():
            return candidate
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


class EngineRoomService:
    def get_snapshot(self) -> Dict[str, Any]:
        compose_config = self._load_compose_config()
        docker_snapshot = self._collect_docker_snapshot(compose_config)
        observability_snapshot = self._collect_observability_snapshot(
            compose_config=compose_config,
            docker_snapshot=docker_snapshot,
        )

        return {
            "scope": "local-only",
            "generated_at": _now_iso(),
            "host": self._collect_host_snapshot(),
            "tools": self._collect_tool_inventory(docker_snapshot),
            "docker": docker_snapshot,
            "observability": observability_snapshot,
        }

    def _collect_host_snapshot(self) -> Dict[str, Any]:
        load_avg = None
        cpu_count = os.cpu_count() or 1
        try:
            load_tuple = os.getloadavg()
            load_avg = [round(value, 2) for value in load_tuple]
        except (AttributeError, OSError):
            load_tuple = None

        cpu_load_percent = None
        if load_tuple:
            cpu_load_percent = round(min((load_tuple[0] / max(cpu_count, 1)) * 100, 100), 1)

        memory = self._read_memory_snapshot()
        disk = shutil.disk_usage(PROJECT_ROOT)

        return {
            "hostname": socket.gethostname(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "uptime": self._read_uptime_snapshot(),
            "cpu": {
                "cores": cpu_count,
                "load_average": load_avg,
                "estimated_load_percent": cpu_load_percent,
                "source": "load_average_per_core" if load_avg else "unavailable",
            },
            "memory": memory,
            "disk": {
                "path": str(PROJECT_ROOT),
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "usage_percent": round((disk.used / disk.total) * 100, 1) if disk.total else None,
            },
        }

    def _read_uptime_snapshot(self) -> Dict[str, Any]:
        if Path("/proc/uptime").exists():
            try:
                uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])
                return {
                    "seconds": int(uptime_seconds),
                    "display": self._format_duration(int(uptime_seconds)),
                    "source": "/proc/uptime",
                }
            except Exception:
                pass

        try:
            result = subprocess.run(
                ["uptime"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {
                    "seconds": None,
                    "display": result.stdout.strip(),
                    "source": "uptime_command",
                }
        except Exception as exc:
            logging.debug("Failed to collect uptime via 'uptime' command: %s", exc)

        return {"seconds": None, "display": "Unavailable", "source": "unavailable"}

    def _read_memory_snapshot(self) -> Dict[str, Any]:
        linux_snapshot = self._read_linux_memory_snapshot()
        if linux_snapshot:
            return linux_snapshot

        darwin_snapshot = self._read_darwin_memory_snapshot()
        if darwin_snapshot:
            return darwin_snapshot

        return {
            "total_bytes": None,
            "used_bytes": None,
            "available_bytes": None,
            "usage_percent": None,
            "source": "unavailable",
        }

    def _read_linux_memory_snapshot(self) -> Optional[Dict[str, Any]]:
        meminfo_path = Path("/proc/meminfo")
        if not meminfo_path.exists():
            return None

        try:
            meminfo: Dict[str, int] = {}
            for line in meminfo_path.read_text().splitlines():
                key, raw = line.split(":", 1)
                match = re.search(r"(\d+)", raw)
                if match:
                    meminfo[key] = int(match.group(1)) * 1024

            total = meminfo.get("MemTotal")
            available = meminfo.get("MemAvailable")
            if not total or available is None:
                return None

            used = total - available
            return {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "usage_percent": round((used / total) * 100, 1) if total else None,
                "source": "/proc/meminfo",
            }
        except Exception:
            return None

    def _read_darwin_memory_snapshot(self) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["vm_stat"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except Exception:
            return None

        if result.returncode != 0 or not result.stdout.strip():
            return None

        try:
            lines = result.stdout.splitlines()
            page_size_match = re.search(r"page size of (\d+) bytes", lines[0])
            page_size = int(page_size_match.group(1)) if page_size_match else 4096

            page_counts: Dict[str, int] = {}
            for line in lines[1:]:
                if ":" not in line:
                    continue
                key, raw = line.split(":", 1)
                match = re.search(r"(\d+)", raw.replace(".", ""))
                if match:
                    page_counts[key.strip()] = int(match.group(1))

            free_pages = page_counts.get("Pages free", 0)
            available_pages = free_pages + page_counts.get("Pages speculative", 0) + page_counts.get("Pages purgeable", 0)
            total_pages = (
                free_pages
                + page_counts.get("Pages active", 0)
                + page_counts.get("Pages inactive", 0)
                + page_counts.get("Pages speculative", 0)
                + page_counts.get("Pages wired down", 0)
                + page_counts.get("Pages occupied by compressor", 0)
            )
            if total_pages <= 0:
                return None

            total = total_pages * page_size
            available = available_pages * page_size
            used = total - available
            return {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "usage_percent": round((used / total) * 100, 1) if total else None,
                "source": "vm_stat",
            }
        except Exception:
            return None

    def _load_compose_config(self) -> Dict[str, Any]:
        if not COMPOSE_FILE.exists():
            return {"path": str(COMPOSE_FILE), "services": []}

        try:
            raw = yaml.safe_load(COMPOSE_FILE.read_text()) or {}
        except Exception:
            return {"path": str(COMPOSE_FILE), "services": []}

        services: List[Dict[str, Any]] = []
        for name, config in (raw.get("services") or {}).items():
            ports: List[Dict[str, Any]] = []
            for entry in config.get("ports", []) or []:
                parsed = self._parse_compose_port(entry)
                if parsed:
                    ports.append(parsed)

            services.append(
                {
                    "name": name,
                    "image": config.get("image"),
                    "profiles": config.get("profiles", []) or [],
                    "ports": ports,
                    "has_healthcheck": bool(config.get("healthcheck")),
                }
            )

        return {"path": str(COMPOSE_FILE), "services": services}

    def _parse_compose_port(self, entry: Any) -> Optional[Dict[str, Any]]:
        if isinstance(entry, int):
            return {"host_port": entry, "container_port": entry, "raw": str(entry)}

        if isinstance(entry, str):
            parts = entry.split(":")
            if len(parts) == 3:
                _, host_port, container_port = parts
            elif len(parts) == 2:
                host_port, container_port = parts
            else:
                host_port = parts[0]
                container_port = parts[0]

            try:
                return {
                    "host_port": int(str(host_port).split("/")[0]),
                    "container_port": int(str(container_port).split("/")[0]),
                    "raw": entry,
                }
            except ValueError:
                return None

        if isinstance(entry, dict):
            published = entry.get("published")
            target = entry.get("target")
            if published and target:
                return {
                    "host_port": int(published),
                    "container_port": int(target),
                    "raw": json.dumps(entry),
                }

        return None

    def _collect_docker_snapshot(self, compose_config: Dict[str, Any]) -> Dict[str, Any]:
        live_state = self._read_docker_compose_state()
        live_by_service = {service["name"]: service for service in live_state.get("services", [])}
        services: List[Dict[str, Any]] = []

        for declared in compose_config.get("services", []):
            host_ports = [port["host_port"] for port in declared.get("ports", [])]
            reachable = any(self._probe_port(port) for port in host_ports) if host_ports else False
            live = live_by_service.get(declared["name"])
            status = "not_running"
            health = "unknown"
            if live:
                status = live.get("state") or status
                health = live.get("health") or health
            elif reachable:
                status = "reachable"

            services.append(
                {
                    "name": declared["name"],
                    "image": declared.get("image"),
                    "profiles": declared.get("profiles", []),
                    "ports": declared.get("ports", []),
                    "has_healthcheck": declared.get("has_healthcheck", False),
                    "reachable": reachable,
                    "state": status,
                    "health": health,
                    "source": live.get("source", "port_probe") if live else "port_probe",
                    "details": live.get("details") if live else None,
                }
            )

        healthy_count = sum(1 for service in services if service["health"] in {"healthy", "running"} or service["state"] == "reachable")
        reachable_count = sum(1 for service in services if service["reachable"])
        live_count = sum(1 for service in services if service["state"] not in {"not_running", "reachable"})

        return {
            "available": live_state["available"],
            "compose_file": compose_config.get("path"),
            "diagnostics": live_state["diagnostics"],
            "services": services,
            "summary": {
                "declared": len(services),
                "reachable": reachable_count,
                "live": live_count,
                "healthy": healthy_count,
            },
        }

    def _read_docker_compose_state(self) -> Dict[str, Any]:
        command = ["docker", "compose", "ps", "--format", "json"]
        diagnostics: List[str] = []

        try:
            result = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except FileNotFoundError:
            return {"available": False, "diagnostics": ["Docker CLI not installed."], "services": []}
        except Exception as exc:
            return {"available": False, "diagnostics": [f"Failed to query Docker: {exc}"], "services": []}

        if result.stderr.strip():
            diagnostics.extend([line for line in result.stderr.splitlines() if line.strip()])

        if result.returncode != 0:
            message = result.stdout.strip() or result.stderr.strip() or "Docker query failed."
            diagnostics.append(message)
            return {"available": False, "diagnostics": diagnostics, "services": []}

        services: List[Dict[str, Any]] = []
        json_payload = result.stdout.strip()
        if json_payload:
            try:
                records = json.loads(json_payload)
                if isinstance(records, dict):
                    records = [records]
            except json.JSONDecodeError:
                records = []
                for line in result.stdout.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("{"):
                        try:
                            records.append(json.loads(stripped))
                        except json.JSONDecodeError:
                            diagnostics.append(f"Failed to parse Docker line: {stripped}")
            for record in records:
                service_name = record.get("Service") or record.get("Name") or ""
                services.append(
                    {
                        "name": service_name,
                        "state": (record.get("State") or "").lower() or "unknown",
                        "health": (record.get("Health") or "").lower() or None,
                        "details": record,
                        "source": "docker_compose_ps",
                    }
                )

        return {"available": True, "diagnostics": diagnostics, "services": services}

    def _collect_observability_snapshot(
        self,
        compose_config: Dict[str, Any],
        docker_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        declared_names = {service["name"] for service in compose_config.get("services", [])}
        docker_by_service = {service["name"]: service for service in docker_snapshot.get("services", [])}

        items = [
            self._observability_item(
                name="Grafana",
                service_name="grafana",
                description="Dashboard surface for local infrastructure signals.",
                url="http://localhost:3000",
                declared_names=declared_names,
                docker_by_service=docker_by_service,
                probe_path="/api/health",
            ),
            self._observability_item(
                name="Prometheus",
                service_name="prometheus",
                description="Metric scraping and target inventory.",
                url="http://localhost:9090",
                declared_names=declared_names,
                docker_by_service=docker_by_service,
                probe_path="/-/ready",
            ),
            self._observability_item(
                name="Loki",
                service_name="loki",
                description="Log aggregation pipeline for local containers.",
                url="http://localhost:3100",
                declared_names=declared_names,
                docker_by_service=docker_by_service,
                probe_path="/ready",
            ),
            self._observability_item(
                name="Langfuse",
                service_name="langfuse",
                description="Tracing and LLM interaction observability.",
                url="http://localhost:3001",
                declared_names=declared_names,
                docker_by_service=docker_by_service,
            ),
        ]

        metrics = self._collect_prometheus_metrics()
        reachable_count = sum(1 for item in items if item["reachable"])
        configured_count = sum(1 for item in items if item["configured"])

        return {
            "items": items,
            "metrics": metrics,
            "summary": {
                "total": len(items),
                "configured": configured_count,
                "reachable": reachable_count,
            },
        }

    def _observability_item(
        self,
        *,
        name: str,
        service_name: str,
        description: str,
        url: str,
        declared_names: set[str],
        docker_by_service: Dict[str, Dict[str, Any]],
        probe_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        declared = service_name in declared_names
        docker_service = docker_by_service.get(service_name, {})
        reachable = self._probe_url(url + probe_path) if probe_path else self._probe_url(url)
        configured = declared or bool(os.getenv("LANGFUSE_HOST")) if service_name == "langfuse" else declared

        return {
            "name": name,
            "service_name": service_name,
            "description": description,
            "url": url,
            "configured": configured,
            "reachable": reachable,
            "state": docker_service.get("state", "not_declared" if not declared else "not_running"),
            "health": docker_service.get("health", "unknown"),
        }

    def _collect_prometheus_metrics(self) -> List[Dict[str, Any]]:
        metrics = [
            {
                "label": "Tracing",
                "value": "Enabled" if bool(os.getenv("LANGFUSE_HOST")) else "Not configured",
                "hint": "Langfuse host binding for local traces.",
                "tone": "good" if os.getenv("LANGFUSE_HOST") else "warn",
            }
        ]

        targets = self._fetch_json("http://localhost:9090/api/v1/targets")
        if not targets:
            metrics.append(
                {
                    "label": "Scrape Targets",
                    "value": "Unavailable",
                    "hint": "Prometheus API is not reachable from the dashboard backend.",
                    "tone": "warn",
                }
            )
            return metrics

        active_targets = targets.get("data", {}).get("activeTargets", [])
        healthy_targets = sum(1 for target in active_targets if target.get("health") == "up")
        metrics.append(
            {
                "label": "Scrape Targets",
                "value": f"{healthy_targets}/{len(active_targets)} healthy",
                "hint": "Active Prometheus targets currently reporting as up.",
                "tone": "good" if healthy_targets == len(active_targets) and active_targets else "warn",
            }
        )
        return metrics

    def _collect_tool_inventory(self, docker_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        github_status = user_connections_store.get_connection_status("github")
        slack_status = user_connections_store.get_connection_status("slack")
        notion_status = user_connections_store.get_connection_status("notion")
        docker_by_service = {service["name"]: service for service in docker_snapshot.get("services", [])}

        items = [
            self._tool_item(
                slug="github",
                name="GitHub",
                category="Code",
                description="Repository, PR, and issue operations for agents and the dashboard owner.",
                configured=github_oauth_client.is_configured() or bool(os.getenv("GITHUB_TOKEN")) or self._has_github_app_credentials(),
                connected=bool(github_status.get("connected")),
                detail=github_status.get("username") or "OAuth or app credentials required.",
            ),
            self._tool_item(
                slug="notion",
                name="Notion",
                category="Knowledge",
                description="Workspace search, page reads, comments, and structured content access.",
                configured=notion_oauth_client.is_configured() or bool(os.getenv("NOTION_API_KEY_ROSSINI")) or bool(os.getenv("NOTION_API_KEY_KOWALSKI")),
                connected=bool(notion_status.get("connected")),
                detail=notion_status.get("username") or "Workspace access can come from OAuth or bot keys.",
            ),
            self._tool_item(
                slug="slack",
                name="Slack",
                category="Comms",
                description="Human approvals, alerts, and bot-mediated coordination.",
                configured=slack_oauth_client.is_configured() or self._has_slack_bot_tokens(),
                connected=bool(slack_status.get("connected")),
                detail=slack_status.get("username") or "Bot tokens or OAuth must be present.",
            ),
            self._tool_item(
                slug="mattermost",
                name="Mattermost",
                category="Comms",
                description="Local team chat channel for the famiglia runtime.",
                configured=bool(os.getenv("MATTERMOST_URL")) or self._has_mattermost_tokens(),
                connected=docker_by_service.get("mattermost", {}).get("reachable", False),
                detail=os.getenv("MATTERMOST_URL", "http://localhost:8065"),
            ),
            self._tool_item(
                slug="web_search",
                name="Web Search",
                category="Research",
                description="Ollama-hosted web search surface used by research workflows.",
                configured=bool(os.getenv("OLLAMA_API_KEY")),
                connected=False,
                detail="Requires OLLAMA_API_KEY for live queries.",
            ),
            self._tool_item(
                slug="duckdb",
                name="DuckDB Warehouse",
                category="Data",
                description="Local data warehouse for observations, staging, and marts.",
                configured=True,
                connected=True,
                detail=os.getenv("DUCKDB_DWH_PATH", str(PROJECT_ROOT / "data" / "duckdb_dwh.db")),
            ),
            self._tool_item(
                slug="ollama",
                name="Ollama Runtime",
                category="Model",
                description="Local model-serving runtime used as the primary inference plane.",
                configured=bool(os.getenv("OLLAMA_HOST")) or bool(os.getenv("OLLAMA_REMOTE_HOST")) or "ollama" in docker_by_service,
                connected=docker_by_service.get("ollama", {}).get("reachable", False),
                detail=os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_REMOTE_HOST") or "http://localhost:11434",
            ),
            self._tool_item(
                slug="langfuse",
                name="Langfuse Traces",
                category="Observability",
                description="Trace and cost visibility for LLM and orchestration flows.",
                configured=bool(os.getenv("LANGFUSE_HOST")),
                connected=docker_by_service.get("langfuse", {}).get("reachable", False),
                detail=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
            ),
        ]

        ready_count = sum(1 for item in items if item["status"] in {"connected", "ready", "online"})
        connected_count = sum(1 for item in items if item["connected"])
        configured_count = sum(1 for item in items if item["configured"])

        return {
            "items": items,
            "summary": {
                "total": len(items),
                "ready": ready_count,
                "connected": connected_count,
                "configured": configured_count,
            },
        }

    def _tool_item(
        self,
        *,
        slug: str,
        name: str,
        category: str,
        description: str,
        configured: bool,
        connected: bool,
        detail: str,
    ) -> Dict[str, Any]:
        if connected:
            status = "connected"
        elif configured:
            status = "ready"
        else:
            status = "inactive"

        if slug in {"duckdb"} and configured:
            status = "online"

        return {
            "slug": slug,
            "name": name,
            "category": category,
            "description": description,
            "configured": configured,
            "connected": connected,
            "status": status,
            "detail": detail,
        }

    def _has_github_app_credentials(self) -> bool:
        keys = [
            "GITHUB_APP_ID_RICCADO",
            "GITHUB_APP_INSTALLATION_ID_RICCADO",
            "GITHUB_APP_PRIVATE_KEY_RICCADO",
            "GITHUB_APP_ID_ROSSINI",
            "GITHUB_APP_INSTALLATION_ID_ROSSINI",
            "GITHUB_APP_PRIVATE_KEY_ROSSINI",
        ]
        return any(os.getenv(key) for key in keys)

    def _has_slack_bot_tokens(self) -> bool:
        return any(
            os.getenv(key)
            for key in [
                "SLACK_APP_TOKEN",
                "SLACK_BOT_TOKEN_SYSTEM",
                "SLACK_BOT_TOKEN_ALFREDO",
                "SLACK_BOT_TOKEN_ROSSINI",
            ]
        )

    def _has_mattermost_tokens(self) -> bool:
        return any(
            os.getenv(key)
            for key in [
                "MATTERMOST_BOT_TOKEN_SYSTEM",
                "MATTERMOST_BOT_TOKEN_ALFREDO",
                "MATTERMOST_BOT_TOKEN_ROSSINI",
            ]
        )

    def _probe_port(self, port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", int(port)), timeout=0.35):
                return True
        except OSError:
            return False

    def _probe_url(self, url: str) -> bool:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "famiglia-engine-room"})
            with urllib.request.urlopen(request, timeout=0.75) as response:
                return 200 <= response.status < 500
        except Exception:
            return False

    def _fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "famiglia-engine-room"})
            with urllib.request.urlopen(request, timeout=1.0) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError):
            return None

    def _format_duration(self, seconds: int) -> str:
        remaining = max(seconds, 0)
        days, remaining = divmod(remaining, 86400)
        hours, remaining = divmod(remaining, 3600)
        minutes, remaining = divmod(remaining, 60)

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if remaining or not parts:
            parts.append(f"{remaining}s")
        return " ".join(parts)


engine_room_service = EngineRoomService()
