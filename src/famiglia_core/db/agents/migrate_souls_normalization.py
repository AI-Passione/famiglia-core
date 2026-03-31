import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from famiglia_core.db.agents.context_store import context_store
from famiglia_core.agents.souls.soul_registry import SOUL_REGISTRY

class SoulMigrator:
    def __init__(self):
        self.sql_dir = Path(__file__).resolve().parent
        self.souls_dir = Path(__file__).resolve().parent.parent.parent / "agents" / "souls"
        self.features_dir = Path(__file__).resolve().parent.parent.parent / "agents" / "orchestration" / "features"
        
    def _scrape_features_workflows(self) -> List[Dict[str, Any]]:
        workflows = []
        if not self.features_dir.exists():
            return workflows
            
        for root, dirs, files in os.walk(self.features_dir):
            for file in files:
                if not file.endswith(".py") or file == "__init__.py":
                    continue
                path = Path(root) / file
                category = path.parent.name
                if category in ("features", "templates", "utils", "__pycache__"):
                    continue
                    
                workflow_name = file[:-3]
                content = path.read_text(encoding="utf-8")
                
                nodes = []
                # Deduplicate nodes while preserving order
                seen = set()
                for m in re.finditer(r'add_node\(\s*["\']([^"\']+)["\']', content):
                    n = m.group(1)
                    if n not in seen:
                        seen.add(n)
                        nodes.append({"name": n, "type": "task"})
                
                workflows.append({
                    "name": workflow_name,
                    "description": f"Automated workflow: {workflow_name}",
                    "category": category,
                    "nodes": nodes
                })
        return workflows

    def apply_schema(self):
        """Applies the new SQL schema files."""
        # Order matters
        schema_files = ["souls.sql", "tools.sql", "skills.sql", "workflows.sql", "resources.sql"]
        for schema_file in schema_files:
            path = self.sql_dir / schema_file
            if not path.exists(): continue
            print(f"[Migrator] Applying {schema_file}...")
            with open(path, "r") as f:
                sql = f.read()
                try:
                    with context_store.db_session() as cursor:
                        if cursor: cursor.execute(sql)
                except Exception as e:
                    print(f"[Migrator] Error applying {schema_file}: {e}")

    def parse_markdown_soul(self, content: str) -> Dict[str, Any]:
        """Extremely basic parser to extract seeding data from Markdown souls."""
        data = {
            "persona": "",
            "reply_constraints": "",
            "identity": "",
            "skills": [],
            "tools": [],
            "workflows": [],
            "resources": []
        }

        # Use an index-based split approach for reliable section extraction
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        for section in sections:
            lines = section.strip().split("\n")
            if not lines: continue
            header = lines[0].strip().upper()
            body = "\n".join(lines[1:]).strip()

            if "PERSONA" in header: data["persona"] = body
            elif "REPLY CONSTRAINTS" in header: data["reply_constraints"] = body
            elif "IDENTITY" in header or "PHRASES" in header: data["identity"] = body
            elif "SKILLS" in header:
                for line in body.split("\n"):
                    m = re.match(r"-\s+\*\*(.*?)\*\*:", line.strip())
                    if m:
                        name = m.group(1).strip()
                        if 5 <= len(name) <= 50:
                            data["skills"].append({"name": name, "description": line.split(":", 1)[1].strip()})
            elif "WORKFLOW" in header:
                for line in body.split("\n"):
                    if line.strip().startswith("- `"):
                        m = re.match(r"-\s+`([\w_]+).*?`", line.strip())
                        if m:
                            data["workflows"].append(m.group(1))
            elif "RESOURCES" in header or "RESOURCE" in header:
                for line in body.split("\n"):
                    if line.strip().startswith("- "):
                        m = re.match(r"-\s+\*\*(.*?)\*\*:\s+(.*)", line.strip())
                        if m:
                            data["resources"].append({"name": m.group(1), "description": m.group(2), "type": "documentation"})
                        else:
                            name = line.strip()[2:]
                            if name: data["resources"].append({"name": name, "description": "", "type": "documentation"})

        # Extract tools via TRIGGER pattern anywhere
        tool_triggers = re.findall(r"\[TRIGGER:\s+(.*?)\((.*?)\)\]", content)
        seen_tools = set()
        for tool_name, _ in tool_triggers:
            plugin = self._guess_plugin(tool_name)
            if plugin not in seen_tools:
                data["tools"].append({"name": plugin, "plugin": plugin})
                seen_tools.add(plugin)

        return data

    def _guess_plugin(self, tool_name: str) -> str:
        if "github" in tool_name.lower(): return "github"
        if "notion" in tool_name.lower(): return "notion"
        if "search" in tool_name.lower(): return "web_search"
        if "duckdb" in tool_name.lower() or "query" in tool_name.lower(): return "duckdb"
        return "system"

    def migrate(self):
        """Performs migration and seeding for Agents and Archetypes."""
        self.apply_schema()
        print("[Migrator] Clearing existing data...")
        with context_store.db_session() as cursor:
            if cursor:
                for t in ["shared_soul_baseline", "agent_tools", "agent_skills", "agent_workflows", "agent_resources", "tools", "skills", "workflows", "workflow_nodes", "resources", "agents", "archetypes"]:
                    cursor.execute(f"DELETE FROM {t}")

        archetypes = [
            {"name": "Butler", "source": "alfredo", "desc": "Handles orchestration, task tracking, and high-level service for Don Jimmy."},
            {"name": "Data Engineer", "source": "riccado", "desc": "Focuses on infrastructure, data pipelines, and database operations."},
            {"name": "Product Strategist", "source": "rossini", "desc": "Provides high-level analysis, product direction, and market context."},
            {"name": "Data Analyst", "source": "kowalski", "desc": "Deep-dives into analytics, pattern recognition, and detailed reporting."},
            {"name": "Operations Support", "source": "bella", "desc": "Facilitates communication, general assistance, and logistics."},
            {"name": "Personal Assistant", "source": "bella", "desc": "Provides direct support, scheduling, and administrative coordination."},
            {"name": "Advisor", "source": "vito", "desc": "Offers strategic guidance, legal perspectives, and wise counsel."}
        ]
        archetype_ids = {}
        with context_store.db_session() as cursor:
            if cursor:
                for arch in archetypes:
                    # Extract template from source agent if provided
                    p, r, i = None, None, None
                    if arch.get("source"):
                        source_path = self.souls_dir / f"{arch['source']}.md"
                        if source_path.exists():
                            src_data = self.parse_markdown_soul(source_path.read_text(encoding="utf-8"))
                            p, r, i = src_data["persona"], src_data["reply_constraints"], src_data["identity"]

                    cursor.execute(
                        """
                        INSERT INTO archetypes (name, description, persona_template, reply_constraints_template, identity_template) 
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                        """, 
                        (arch["name"], arch["desc"], p, r, i)
                    )
                    archetype_ids[arch["name"]] = cursor.fetchone()["id"]

        mapping = {
            "alfredo": "Butler", 
            "riccado": "Data Engineer", 
            "rossini": "Product Strategist",
            "kowalski": "Data Analyst", "tommy": "Data Analyst", 
            "vito": "Advisor",
            "bella": "Personal Assistant"
        }
        
        inactive_agents = {"vito", "tommy", "bella"}

        # 2. Seed Shared Soul Baseline
        shared_path = self.souls_dir / "souls.md"
        if shared_path.exists():
            print("[Migrator] Seeding shared_soul_baseline...")
            with context_store.db_session() as cursor:
                if cursor: cursor.execute("INSERT INTO shared_soul_baseline (content) VALUES (%s)", (shared_path.read_text(encoding="utf-8"),))

        # 3. Seed Core Tools
        core_tools = [
            {"name": "github", "plugin": "github", "desc": "Access to GitHub for code review."},
            {"name": "notion", "plugin": "notion", "desc": "Access to Notion for documentation."},
            {"name": "duckdb", "plugin": "duckdb", "desc": "Access to the Local Data Warehouse."},
            {"name": "web_search", "plugin": "web_search", "desc": "Access to live web search."}
        ]
        tool_ids = {}
        with context_store.db_session() as cursor:
            if cursor:
                for t in core_tools:
                    cursor.execute("INSERT INTO tools (name, description, plugin) VALUES (%s, %s, %s) RETURNING id", (t["name"], t["desc"], t["plugin"]))
                    tool_ids[t["name"]] = cursor.fetchone()["id"]

        # 4. Scrape and Seed Workflows from features directory
        scraped_workflows = self._scrape_features_workflows()
        workflow_ids = {}
        print(f"[Migrator] Seeding {len(scraped_workflows)} workflows from features directory...")
        for wf in scraped_workflows:
            print(f"[Migrator] Discovered workflow: {wf['name']}")
            with context_store.db_session() as cursor:
                if cursor:
                    cursor.execute("INSERT INTO workflows (name, description, category, node_order) VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO UPDATE SET node_order = EXCLUDED.node_order RETURNING id", (wf["name"], wf["description"], wf["category"], [n["name"] for n in wf["nodes"]]))
                    wid = cursor.fetchone()["id"]
                    workflow_ids[wf["name"]] = wid
                    for n in wf["nodes"]: 
                        cursor.execute("INSERT INTO workflow_nodes (workflow_id, node_name, node_type) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (wid, n["name"], n["type"]))

        SKILL_BLOCKLIST = {"conciseness", "standards", "fact-only", "actionable advice", "clarity"}

        print("[Migrator] Seeding agents and traits...")
        for agent_id, config in SOUL_REGISTRY.items():
            soul_path = self.souls_dir / f"{agent_id}.md"
            if not soul_path.exists(): continue
            content = soul_path.read_text(encoding="utf-8")
            parsed_data = self.parse_markdown_soul(content)
            arch_id = archetype_ids.get(mapping.get(agent_id))
            is_active = agent_id not in inactive_agents
            context_store.upsert_agent_soul(
                agent_id, 
                agent_id.capitalize(), 
                persona=parsed_data["persona"], 
                reply_constraints=parsed_data["reply_constraints"], 
                identity=parsed_data["identity"], 
                aliases=config.get("aliases", []), 
                archetype_id=arch_id,
                is_active=is_active
            )

            active_tools = {t["plugin"] for t in parsed_data["tools"]}
            for kw in ["github", "notion", "web search"]:
                if kw in content.lower(): active_tools.add(kw.replace(" ", "_"))
            for t_name in active_tools:
                if t_name in tool_ids:
                    with context_store.db_session() as cursor:
                        if cursor: cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (agent_id, tool_ids[t_name]))

            for skill in parsed_data["skills"]:
                if skill["name"].lower() in SKILL_BLOCKLIST: continue
                with context_store.db_session() as cursor:
                    if cursor:
                        cursor.execute("INSERT INTO skills (name, description) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description RETURNING id", (skill["name"], skill["description"]))
                        sid = cursor.fetchone()["id"]
                        cursor.execute("INSERT INTO agent_skills (agent_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (agent_id, sid))

            for wf_name in parsed_data["workflows"]:
                if wf_name in workflow_ids:
                    print(f"[Migrator] Linking agent {agent_id} to workflow {wf_name}")
                    wid = workflow_ids[wf_name]
                    with context_store.db_session() as cursor:
                        if cursor:
                            cursor.execute("INSERT INTO agent_workflows (agent_id, workflow_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (agent_id, wid))
                else:
                    print(f"[Migrator] Warning: Agent {agent_id} requested unknown workflow '{wf_name}'")

            for res in parsed_data["resources"]:
                print(f"[Migrator] Inserting resource for {agent_id}: {res['name']}")
                with context_store.db_session() as cursor:
                    if cursor:
                        cursor.execute("INSERT INTO resources (name, description, type) VALUES (%s, %s, %s) ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description RETURNING id", (res["name"], res["description"], res["type"]))
                        rid = cursor.fetchone()["id"]
                        cursor.execute("INSERT INTO agent_resources (agent_id, resource_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (agent_id, rid))

if __name__ == "__main__":
    SoulMigrator().migrate()
