import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import requests
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

from famiglia_core.db.agents.context_store import context_store
# Langfuse imports removed to avoid OTel 404s
# Tracing is handled by BaseAgent via CallbackHandler

# ---------------------------------------------------------------------------
# Tier prefixes used in model_config dicts
#   "gemini-*"          → Tier 1 cloud (Gemini)
#   "perplexity-*"      → Tier 1 cloud (Perplexity)
#   "claude-*"          → Tier 1 cloud (Anthropic)
#   "ollama-*"          → Tier 2 local Ollama (OLLAMA_HOST)
#   "remote-ollama-*"   → Tier 3 self-hosted Ollama (OLLAMA_REMOTE_HOST)
# ---------------------------------------------------------------------------

from famiglia_core.agents.llm.models_registry import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_FALLBACK_MODEL  # noqa: E402

_CLOUD_PREFIXES = ("gemini", "perplexity", "claude")
# Kept for backward-compatibility with any external references.
DEFAULT_OLLAMA_MODEL_TAG = DEFAULT_OLLAMA_MODEL


class LLMClient:
    @staticmethod
    def _ensure_url(host: str) -> str:
        """Helper to ensure a host string is a valid URL with scheme and port."""
        if not host:
            return ""
        # Add scheme if missing
        if "://" not in host:
            host = f"http://{host}"
        # Add default port if missing and no port specified
        # Check if there's a port after the last colon (excluding the scheme)
        parts = host.split("://", 1)
        if ":" not in parts[1]:
            host = f"{host}:11434"
        return host

    def __init__(self):
        # Tier 2: local Ollama (default http://127.0.0.1:11434)
        self.ollama_host = self._ensure_url(os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"))
        # Tier 3: remote self-hosted Ollama server
        self.ollama_remote_host = self._ensure_url(os.getenv("OLLAMA_REMOTE_HOST", "http://192.168.178.166:11434"))
        self.default_ollama_model = os.getenv("OLLAMA_FALLBACK_MODEL", DEFAULT_OLLAMA_MODEL)
        self.session = requests.Session()

        self._ollama_bootstrapped = False
        self._ollama_process: Optional[subprocess.Popen] = None
        self._generation_lock = threading.Lock()
        self.allocated_models: Dict[str, str] = {}

        self.providers: Dict[str, Callable[[str], str]] = {
            "gemini-2.0-flash": self._mock_gemini,
            "perplexity-sonar-pro": self._mock_perplexity,
            "claude-code": self._mock_claude_code,
            "claude-3.7-sonnet": self._mock_claude_code,
        }

        self._last_seen_models: Dict[str, set[str]] = {self.ollama_host: set()}
        if self.ollama_remote_host:
            self._last_seen_models[self.ollama_remote_host] = set()
        
        self._monitor_thread = threading.Thread(target=self._ram_monitor_loop, daemon=True)
        self._monitor_thread.start()


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(self, prompt: str, model_config: Dict[str, Any], agent_name: str = "", routing_mode: str = "") -> tuple[str, str]:
        # Tracing is now handled by CallbackHandler in BaseAgent
        # Generation metadata will still be captured by the LangChain callback if using LangChain models.
        
        primary = model_config.get("primary")
        global_fallback = model_config.get("global_fallback")

        if routing_mode:
            enrichment = (
                f"--- SYSTEM ROUTING CONTEXT ---\n"
                f"You are currently operating in {routing_mode} mode.\n"
                f"If mode is CHAT: Provide conversational responses. No tools allowed.\n"
                f"If mode is TOOL: You must output a valid [TRIGGER: ...] command based on your instructions. Do NOT ask clarifying questions.\n"
                f"If mode is WORKFLOW: You must trigger a predefined system workflow.\n"
                f"If mode is COMPLEX: You are driving a multi-step analytical or strategic workflow.\n\n"
            )
            prompt = enrichment + prompt

        # Fast-track: fetch what was allocated at startup
        allocated_secondary = self.allocated_models.get(agent_name)

        attempts = self._build_attempts(primary, allocated_secondary, global_fallback)
        errors: List[str] = []

        for model in attempts:
            if not model:
                continue

            if not self._is_provider_available(model):
                errors.append(f"{model}: unavailable")
                continue

            try:
                print(f"[LLM Client] Trying provider {model}...")
                res = self._dispatch(prompt, model, model_config.get("options"))
                print(f"[LLM Client] Success with {model}!")
                return res, model
            except Exception as exc:
                print(f"[LLM Client] Error with {model}: {exc}")
                errors.append(f"{model}: {exc}")

        # Deterministic mock fallback when no Ollama service is reachable at all.
        if not self._is_ollama_service_available() and not self._is_remote_ollama_available():
            print("[LLM Client] All Ollama hosts unavailable; returning mock fallback response.")
            return self._mock_ollama(prompt), "mock-fallback"

        print(f"[LLM Client] All configured LLM providers failed: {errors}")
        raise ValueError(f"All configured LLM providers failed ({'; '.join(errors)})")

    def ensure_ollama_ready(self, auto_pull: bool = True) -> bool:
        """Try Tier 2 (local) first, then Tier 3 (remote)."""
        if self._ollama_bootstrapped and (
            self._is_ollama_service_available() or self._is_remote_ollama_available()
        ):
            return True

        # Tier 2: local Ollama (running service or startable local binary)
        if self._ensure_local_ollama_ready(auto_pull=auto_pull):
            return True

        # Tier 3: remote Ollama fallback
        if self._is_remote_ollama_available():
            self._ollama_bootstrapped = True
            if auto_pull:
                self._ensure_model_pulled(self.default_ollama_model, host=self.ollama_remote_host)
            print(f"[LLM] Remote Ollama available at {self.ollama_remote_host}")
            return True

        return False

    def _ensure_local_ollama_ready(self, auto_pull: bool = True) -> bool:
        # Tier 2a: local Ollama service already running
        if self._is_ollama_service_available():
            self._ollama_bootstrapped = True
            if auto_pull:
                self._ensure_model_pulled(self.default_ollama_model, host=self.ollama_host)
            return True

        # Tier 2b: start local Ollama binary if available
        if not shutil.which("ollama"):
            print("[LLM] Local Ollama binary not found. Falling back to remote Ollama if reachable.")
            return False

        print("[LLM] Starting local Ollama service...")
        self._ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not self._wait_for_ollama():
            print("[LLM] Ollama did not become ready in time.")
            return False

        if auto_pull:
            self._ensure_model_pulled(self.default_ollama_model, host=self.ollama_host)

        self._ollama_bootstrapped = True
        return True

    def get_model_status_report(self) -> Dict[str, Dict[str, bool]]:
        """Check availability of all required models across reachable hosts."""
        required = set()
        required.add(self._ollama_model_from_name(self.default_ollama_model))
        for model in self.allocated_models.values():
            if not any(model.startswith(p) for p in _CLOUD_PREFIXES):
                required.add(self._ollama_model_from_name(model))

        report = {}
        local_tags = self._get_available_models(self.ollama_host)
        remote_tags = self._get_available_models(self.ollama_remote_host)

        for model in required:
            report[model] = {
                "local": self._model_exists_in_tags(model, local_tags),
                "remote": self._model_exists_in_tags(model, remote_tags)
            }
        return report

    def _model_exists_in_tags(self, model: str, tags: set[str]) -> bool:
        """Robustly check if a model exists in available tags."""
        if not tags:
            return False
        
        # Exact match
        if model in tags:
            return True
        
        # Case-insensitive match and handling for :latest
        m_lower = model.lower()
        t_lower = {t.lower() for t in tags}
        
        if m_lower in t_lower:
            return True
            
        if ":" not in m_lower:
            if f"{m_lower}:latest" in t_lower:
                return True
        elif m_lower.endswith(":latest"):
            if m_lower.replace(":latest", "") in t_lower:
                return True
                
        return False

    def _get_available_models(self, host: str) -> set[str]:
        if not host:
            return set()
        url = f"{host}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
                return {m.get("name") for m in body.get("models", [])}
        except Exception:
            return set()

    def resolve_best_model(self, model_config: Dict[str, Any], agent_name: str = "") -> str:
        """
        Public helper to determine the single best available model from a config.
        Follows the 3-tier priority (Cloud -> Local -> Remote Fallback).
        """
        primary = model_config.get("primary")
        secondary = self.allocated_models.get(agent_name) or model_config.get("secondary")
        global_fallback = model_config.get("global_fallback") or self.default_ollama_model

        attempts = self._build_attempts(primary, secondary, global_fallback)
        
        for model in attempts:
            if model and self._is_provider_available(model):
                return model
        
        return self.default_ollama_model

    def allocate_resources(self, agents: List[Any]) -> None:
        """Evaluate system memory and allocate local models to agents based on priority."""
        if not self.ensure_ollama_ready(auto_pull=False):
            return

        try:
            available_gb = self._get_available_ram_gb()
            print(f"[LLM] Available System RAM for models: {available_gb:.1f}GB")
        except Exception:
            available_gb = 8.0
            print(f"[LLM] Could not resolve system RAM, defaulting to {available_gb}GB pool")

        try:
            stats = context_store.get_agent_interaction_stats()
        except Exception as e:
            print(f"[LLM] Warning: Could not fetch interaction stats: {e}")
            stats = {}

        def get_agent_score(agent):
            name = getattr(agent, "name", "")
            agent_stats = stats.get(name, {})
            last_active = agent_stats.get("last_active", datetime.min.replace(tzinfo=timezone.utc))
            msg_count = agent_stats.get("msg_count", 0)
            return (last_active, msg_count)

        sorted_agents = sorted(agents, key=get_agent_score, reverse=True)

        for agent in sorted_agents:
            agent_name = getattr(agent, "name", "")
            model_config = getattr(agent, "model_config", {})
            secondary = model_config.get("secondary")
            global_fallback = model_config.get("global_fallback")

            allocated_model = global_fallback or self.default_ollama_model

            if secondary:
                if any(secondary.startswith(prefix) for prefix in _CLOUD_PREFIXES):
                    self.allocated_models[agent_name] = secondary
                    continue
                # Assign on-demand — no RAM check or pre-pull at startup
                allocated_model = secondary
                print(f"[LLM] Assigned {secondary} to {agent_name} (on-demand loading enabled).")

            self.allocated_models[agent_name] = allocated_model

            # Proactive pull — download model binary for both Tier 2 and Tier 3 if available
            if not allocated_model.startswith(_CLOUD_PREFIXES):
                clean_model = self._ollama_model_from_name(allocated_model)
                if self._is_ollama_service_available():
                    self._ensure_model_pulled(clean_model, host=self.ollama_host)
                if self._is_remote_ollama_available():
                    self._ensure_model_pulled(clean_model, host=self.ollama_remote_host)

    # ------------------------------------------------------------------
    # Internal: attempt ordering
    # ------------------------------------------------------------------

    def _build_attempts(
        self,
        primary: Optional[str],
        secondary: Optional[str],
        global_fallback: Optional[str],
    ) -> List[str]:
        """Build an ordered list of models to try, enforcing the 3-tier priority:
        cloud AI → local Ollama → remote Ollama.
        """
        raw = [primary, secondary, global_fallback]

        # Always ensure a local-ollama sentinel is present (Tier 2)
        if not any(m and (m.startswith("ollama-") or ":" in m) for m in raw):
            raw.append(f"ollama-{self.default_ollama_model.split(':')[0]}")

        # Always ensure a remote-ollama sentinel is present (Tier 3)
        if not any(m and m.startswith("remote-ollama-") for m in raw):
            raw.append(f"remote-ollama-{self.default_ollama_model.replace(':', '-')}")

        # Stable sort: cloud first, then local ollama, then remote-ollama
        def tier(m: Optional[str]) -> int:
            if not m:
                return 99
            # Cloud Tier 0
            if any(m.startswith(p) for p in _CLOUD_PREFIXES):
                return 0
            # Tier 3 Remote
            if m.startswith("remote-ollama-"):
                return 2
            # Tier 1 Local (if it starts with ollama- OR has a tag like mistral:7b)
            if m.startswith("ollama-") or ":" in m:
                return 1
            return 3  # unknown – put last

        seen: set = set()
        ordered: List[str] = []
        for model in sorted(raw, key=tier):
            if model and model not in seen:
                seen.add(model)
                ordered.append(model)
        return ordered

    # ------------------------------------------------------------------
    # Internal: availability checks
    # ------------------------------------------------------------------

    def _is_provider_available(self, model: str) -> bool:
        if model.startswith("gemini"):
            return bool(os.getenv("GEMINI_API_KEY"))
        if model.startswith("claude"):
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        if model.startswith("perplexity"):
            return bool(os.getenv("PERPLEXITY_API_KEY"))
        if model.startswith("remote-ollama-"):
            return self._is_remote_ollama_available()
        # Plain ollama-* → Tier 2 local
        return self._ensure_local_ollama_ready(auto_pull=False)

    def _is_remote_ollama_available(self) -> bool:
        """Probe the remote Ollama host (Tier 3)."""
        if not self.ollama_remote_host:
            return False
        url = f"{self.ollama_remote_host}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:
            return False

    def _is_ollama_service_available(self) -> bool:
        """Probe the local Ollama host (Tier 2)."""
        url = f"{self.ollama_host}/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            return False

    def _wait_for_ollama(self, max_attempts: int = 20) -> bool:
        for _ in range(max_attempts):
            if self._is_ollama_service_available():
                return True
            time.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    # Internal: dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, prompt: str, model: str, options: Optional[Dict[str, Any]]) -> str:
        """Route to the right backend based on model prefix."""
        provider = self.providers.get(model)
        is_cloud = any(model.startswith(p) for p in _CLOUD_PREFIXES)

        if is_cloud:
            if provider:
                return provider(prompt)
            raise ValueError(f"Cloud model '{model}' has no configured provider")

        if model.startswith("remote-ollama-"):
            ollama_model = self._ollama_model_from_name(model.replace("remote-ollama-", "ollama-"))
            return self._ollama_complete(prompt, ollama_model, options=options, host=self.ollama_remote_host)

        # Plain ollama-* → Tier 2 local
        ollama_model = self._ollama_model_from_name(model)
        return self._ollama_complete(prompt, ollama_model, options=options, host=self.ollama_host)

    # ------------------------------------------------------------------
    # Internal: Ollama API
    # ------------------------------------------------------------------

    def _ollama_complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        host: Optional[str] = None,
    ) -> str:
        model_name = model or self.default_ollama_model
        effective_host = host or self.ollama_host
        url = f"{effective_host}/api/generate"

        with self._generation_lock:
            # JIT pull — download model binary if not already local
            self._ensure_model_pulled(model_name, host=effective_host)

            # Evict any OTHER model currently loaded in RAM (on that host)
            self._ensure_offloaded(target_model=model_name, host=effective_host)

            final_options = {
                "use_mmap": True,
                "num_keep": 256,
                "num_thread": 4,
            }
            if options:
                final_options.update(options)

            # default model vs per-agent custom model.
            is_default_model = (model_name == self.default_ollama_model) or \
                               (model_name == self._ollama_model_from_name(self.default_ollama_model))
            
            # Keep the default model in memory forever (-1 means infinite in Ollama API)
            # and give other models 300 seconds of idle time.
            keep_alive = -1 if is_default_model else 300

            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": True,
                "keep_alive": keep_alive,
                "options": final_options,
            }

            try:
                print(f"[LLM Client] Sending request to Ollama at {url}...")
                # print(f"[LLM Client] Prompt attached: {prompt}")
                resp = self.session.post(
                    url,
                    json=payload,
                    stream=True,
                    timeout=300
                )
                resp.raise_for_status()

                full_text = ""
                for line in resp.iter_lines():
                    if line:
                        body = json.loads(line.decode("utf-8"))
                        if body.get("error"):
                            raise RuntimeError(
                                f"Ollama error from {effective_host}: {body.get('error')}"
                            )
                        full_text += body.get("response", "")
                        if body.get("done", False):
                            break

                final_text = full_text.strip()
                if final_text:
                    return final_text

            except requests.exceptions.RequestException as exc:
                raise RuntimeError(f"Cannot reach Ollama at {effective_host}: {exc}") from exc
            except Exception as exc:
                raise RuntimeError(f"Error during Ollama generation: {exc}") from exc

        raise RuntimeError(f"Empty response from Ollama model {model_name} at {effective_host}")

    def _ensure_offloaded(
        self,
        target_model: Optional[str] = None,
        timeout_secs: float = 30.0,
        host: Optional[str] = None,
    ) -> bool:
        """
        Enforce Strict Dual-Model Policy:
        1. Always keep the default fallback model in RAM.
        2. At most ONE other model (the target) can be in RAM.
        3. Any other non-default models are evicted immediately.
        """
        effective_host = host or self.ollama_host
        ps_url = f"{effective_host}/api/ps"
        gen_url = f"{effective_host}/api/generate"
        start = time.time()

        # Canonicalize target name if provided
        target_clean = ""
        if target_model:
            target_clean = self._ollama_model_from_name(target_model).strip()

        # Canonicalize default name
        default_clean = self._ollama_model_from_name(self.default_ollama_model).strip()

        while (time.time() - start) < timeout_secs:
            try:
                with urllib.request.urlopen(ps_url, timeout=2) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    models = data.get("models", [])

                    if not models:
                        # RAM is empty (Ollama might have auto-evicted everything)
                        return True

                    to_evict = []
                    for m in models:
                        loaded_name = m.get("name", "").strip()
                        
                        # 1. Never evict the default model
                        if loaded_name == default_clean or f"{loaded_name}:latest" == default_clean or loaded_name.replace(":latest", "") == default_clean:
                            continue
                        
                        # 3. Busy Check: Avoid evicting models that are currently processing a request
                        # Busy models usually have their expires_at set to infinite (0001-...) 
                        # or a duration longer than our standard 60s keep_alive.
                        expires_at = m.get("expires_at")
                        if expires_at:
                            try:
                                # Parse ISO 8601 (e.g. 2026-03-02T12:00:00Z)
                                dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                                now = datetime.now(timezone.utc)
                                ttl_secs = (dt - now).total_seconds()
                                
                                # If TTL is more than our 60s + 10s buffer, or is essentially infinite (0001-...)
                                # we consider it "Busy" or "Pinned".
                                if ttl_secs > 70 or dt.year < 1000:
                                    # It's busy, don't kick it out regardless of policy
                                    continue
                            except Exception:
                                # If we can't parse it, safer to assume it might be busy
                                continue

                        # 4. Everything else is fair game for eviction (Strict policy)
                        to_evict.append(loaded_name)

                    if not to_evict:
                        return True

                    for name in to_evict:
                        print(f"[LLM] Actively evicting model from RAM: {name}")
                        try:
                            evict_payload = json.dumps({"model": name, "keep_alive": 0}).encode("utf-8")
                            evict_req = urllib.request.Request(
                                gen_url,
                                data=evict_payload,
                                headers={"Content-Type": "application/json"},
                                method="POST",
                            )
                            urllib.request.urlopen(evict_req, timeout=5)
                        except Exception as e:
                            print(f"[LLM] Failed to evict {name}: {e}")

                # Update monitor state to reflect current reality and avoid redundant logs
                self._last_seen_models[effective_host] = {m.get("name", "").strip() for m in models if m.get("name", "").strip() not in to_evict}

            except Exception as e:
                print(f"[LLM Client] Error checking RAM status: {e}")
            
            time.sleep(0.5)

        print(f"[LLM] Warning: Timed out waiting for models to offload after {timeout_secs}s.")
        return False

    def _ram_monitor_loop(self):
        """Background loop to detect and log model evictions (timeouts)."""
        while True:
            time.sleep(10)
            for host in list(self._last_seen_models.keys()):
                try:
                    self._check_host_evictions(host)
                except Exception:
                    pass

    def _check_host_evictions(self, host: str):
        """Check a specific host for models that have disappeared from RAM."""
        url = f"{host}/api/ps"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                current_models = {m.get("name", "").strip() for m in data.get("models", [])}
                
                last_seen = self._last_seen_models.get(host, set())
                
                # Models that were there but are gone now
                evicted = last_seen - current_models
                for model in evicted:
                    # Ignore if it's the default model (shouldn't happen with keep_alive: None)
                    default_clean = self._ollama_model_from_name(self.default_ollama_model).strip()
                    if model == default_clean or f"{model}:latest" == default_clean:
                        continue
                    
                    print(f"[LLM] Model evicted from RAM (Timeout/Policy) at {host}: {model}")
                
                self._last_seen_models[host] = current_models
        except Exception:
            pass

    def _ensure_model_pulled(self, model: str, host: Optional[str] = None) -> None:
        effective_host = host or self.ollama_host
        tags_url = f"{effective_host}/api/tags"
        try:
            with urllib.request.urlopen(tags_url, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            print(f"[LLM] Failed to list Ollama models at {effective_host}: {exc}")
            return

        available = {m.get("name") for m in body.get("models", [])}
        print(f"[LLM] Checking canonical model tag: {model} at {effective_host}")
        if self._model_exists_in_tags(model, available):
            print(f"[LLM] Model {model} is already present at {effective_host}. Skipping pull.")
            return

        print(f"[LLM] Model {model} MISSING at {effective_host}. Initializing pull request...")
        pull_url = f"{effective_host}/api/pull"
        payload = {"model": model, "stream": True}
        
        try:
            resp = self.session.post(
                pull_url,
                json=payload,
                stream=True,
                timeout=1800  # 30 minute timeout for large model pulls
            )
            resp.raise_for_status()
            
            last_status = ""
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    
                    if data.get("error"):
                        error_msg = data.get("error")
                        print(f"[LLM] CRITICAL: Ollama pull error for {model}: {error_msg}")
                        raise RuntimeError(f"Ollama pull failed: {error_msg}")

                    status = data.get("status", "")
                    if status and status != last_status:
                        if "pulling" in status.lower() or "verifying" in status.lower():
                            if ":" not in status: 
                                print(f"  [Ollama] {model}: {status}")
                        last_status = status
            
            print(f"[LLM] Completed pull of {model} from {effective_host}")
            return
        except Exception as exc:
            print(f"[LLM] CRITICAL: Failed to pull Ollama model {model} from {effective_host}: {exc}")
            # We don't raise here to allow potential Tier 3 fallback attempts


    # ------------------------------------------------------------------
    # Internal: model name resolution
    # ------------------------------------------------------------------

    def _ollama_model_from_name(self, model_name: str) -> str:
        clean = model_name.replace("ollama-", "").replace("remote-ollama-", "")
        # Map shorthand aliases → canonical Ollama model tags
        _aliases = {
            "gemma3": "gemma3:4b",
            "gemma3-4b": "gemma3:4b",
            "gemma3-1b": "gemma3:1b",
            "gemma4": "gemma4:e2b",
            "gemma4-e2b": "gemma4:e2b",
            "gemma4_e2b": "gemma4:e2b",
            "llama3": "llama3",
            "qwen2.5": "qwen2.5:3b-instruct-q4_0",
            "qwen2.5-3b": "qwen2.5:3b-instruct-q4_0",
            "qwen2.5-7b": "qwen2.5:7b",
            "qwen3-4b": "qwen3:4b",
            "qwen3.5": "qwen3.5:4b",
            "qwen3.5-4b": "qwen3.5:4b",
            "qwen3.5-9b": "qwen3.5:9b",
        }
        return _aliases.get(clean, clean)

    # ------------------------------------------------------------------
    # Internal: RAM check
    # ------------------------------------------------------------------

    def _get_required_ram_gb(self, model_name: str) -> float:
        clean_name = model_name.replace("ollama-", "").replace("remote-ollama-", "")
        if "gemma3:1b" in clean_name.lower():
            return 0.0
        lower_name = clean_name.lower()
        if "9b" in lower_name:
            return 7.0
        if "7b" in lower_name or "6.7b" in lower_name or "qwen2.5:7b" in lower_name:
            return 5.0
        if "3b" in lower_name:
            return 3.0
        elif "gemma4" in lower_name or "e2b" in lower_name:
            return 2.5
        elif "4b" in lower_name or "qwen3.5" in lower_name or "3.5" in lower_name or "2b" in lower_name:
            return 4.0
        return 4.0

    def _get_available_ram_gb(self) -> float:
        """Get available RAM in GB supporting both macOS and Linux (Docker)."""
        if os.path.exists("/sys/fs/cgroup/memory.max"):
            try:
                with open("/sys/fs/cgroup/memory.max", "r") as f:
                    limit = f.read().strip()
                    if limit != "max":
                        with open("/sys/fs/cgroup/memory.current", "r") as fc:
                            current = int(fc.read().strip())
                            return (int(limit) - current) / (1024**3)
            except Exception as e:
                print(f"[LLM] Error reading cgroups v2: {e}")

        if os.path.exists("/sys/fs/cgroup/memory/memory.limit_in_bytes"):
            try:
                with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as f:
                    limit = int(f.read().strip())
                    if limit < 9000000000000000000:
                        with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as fc:
                            current = int(fc.read().strip())
                            return (limit - current) / (1024**3)
            except Exception as e:
                print(f"[LLM] Error reading cgroups v1: {e}")

        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo", "r") as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            name = parts[0].strip()
                            value = parts[1].split()[0]
                            meminfo[name] = int(value) * 1024
                    calc_avail = (
                        meminfo.get("MemFree", 0)
                        + meminfo.get("Buffers", 0)
                        + meminfo.get("Cached", 0)
                    ) / (1024**3)
                    print(f"[LLM Client] /proc/meminfo parsed available: {calc_avail:.1f}GB")
                    return max(calc_avail, meminfo.get("MemAvailable", 0) / (1024**3))
            except Exception as e:
                print(f"[LLM] Error reading /proc/meminfo: {e}")

        try:
            if shutil.which("vm_stat"):
                output = subprocess.check_output(["vm_stat"]).decode("utf-8")
                stats = {}
                for line in output.split("\n"):
                    if ":" in line:
                        key, val = line.split(":")
                        stats[key.strip()] = int(val.strip().replace(".", ""))
                page_size = 16384 if "page size of 16384 bytes" in output else 4096
                available_pages = (
                    stats.get("Pages free", 0)
                    + stats.get("Pages speculative", 0)
                    + stats.get("Pages inactive", 0)
                )
                return (available_pages * page_size) / (1024**3)
        except Exception as e:
            print(f"[LLM] OS check failed: {e}")

        return 8.0

    # ------------------------------------------------------------------
    # Mocks (used by tests and cloud provider stubs)
    # ------------------------------------------------------------------

    def _mock_gemini(self, prompt: str) -> str:
        return "I have processed your request of the family business. What else? (Gemini mock)"

    def _mock_perplexity(self, prompt: str) -> str:
        return "I have analyzed the market data for you. (Perplexity mock)"

    def _mock_claude_code(self, prompt: str) -> str:
        return "The code changes have been reviewed. (Claude mock)"

    def _mock_ollama(self, prompt: str) -> str:
        return "Local processing complete. (Ollama mock)"


# Singleton instance
client = LLMClient()
