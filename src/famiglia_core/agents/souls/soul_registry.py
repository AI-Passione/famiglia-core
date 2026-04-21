import re
from pathlib import Path
from typing import Dict, List


SOUL_REGISTRY: Dict[str, Dict[str, List[str]]] = {
    "alfredo": {"aliases": ["alfredo"]},
    "riccardo": {"aliases": ["riccardo"]},
    "bella": {"aliases": ["bella"]},
    "rossini": {"aliases": ["dr rossini", "rossini"]},
    "vito": {"aliases": ["vito"]},
    "tommy": {"aliases": ["tommy"]},
    "kowalski": {"aliases": ["kowalski"]},
    "giuseppina": {"aliases": ["giuseppina"]},
}


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _soul_path_for(agent_id: str) -> Path:
    # Now that soul_registry.py is in src/agents/souls/
    root_dir = Path(__file__).resolve().parent
    return root_dir / f"{agent_id}.md"


def resolve_agent_id(agent_name: str, agent_id: str = "") -> str:
    if agent_id:
        resolved = _normalize_name(agent_id)
        if resolved in SOUL_REGISTRY:
            return resolved
        raise ValueError(f"Unknown agent_id '{agent_id}' for soul registry.")

    normalized_name = _normalize_name(agent_name)
    for known_id, config in SOUL_REGISTRY.items():
        aliases = config.get("aliases", [])
        alias_set = {_normalize_name(a) for a in aliases}
        alias_set.add(_normalize_name(known_id))
        if normalized_name in alias_set:
            return known_id

    raise ValueError(f"Cannot resolve agent_id from agent name '{agent_name}'.")


def load_agent_soul(agent_id: str, agent_name: str) -> str:
    from famiglia_core.db.agents.context_store import context_store
    
    resolved_id = resolve_agent_id(agent_name=agent_name, agent_id=agent_id)
    
    # 1. Try to load from Database first
    db_soul = context_store.get_agent_soul(resolved_id)
    db_traits = context_store.get_agent_traits(resolved_id)
    
    if db_soul:
        print(f"[SoulRegistry] Loading soul from database for {resolved_id}")
        
        # Load shared baseline from DB or file fallback
        shared_text = context_store.get_shared_soul_baseline()
        if not shared_text:
            shared_path = Path(__file__).resolve().parent / "souls.md"
            if shared_path.exists():
                shared_text = shared_path.read_text(encoding="utf-8").strip()
        
        # Build the soul string from normalized fields
        parts = []
        if shared_text:
            parts.append(shared_text)
            
        if db_soul.get("persona"):
            parts.append(f"## PERSONA & TONE\n{db_soul['persona']}")
        if db_soul.get("reply_constraints"):
            parts.append(f"## REPLY CONSTRAINTS\n{db_soul['reply_constraints']}")
        if db_soul.get("identity"):
            parts.append(f"## PHRASES & IDENTITY\n{db_soul['identity']}")
            
        # Add Traits
        if db_traits["skills"]:
            skills_text = "\n".join([f"- **{s['name']}**: {s.get('description', '')}" for s in db_traits["skills"]])
            parts.append(f"## SPECIALIZED SKILLS\n{skills_text}")
            
        if db_traits["tools"]:
            tools_text = "\n".join([f"- `{t['name']}`: {t.get('description', '')} (Plugin: {t.get('plugin', 'system')})" for t in db_traits["tools"]])
            parts.append(f"## AVAILABLE TOOLS\n{tools_text}")
            
        if db_traits["workflows"]:
            wf_text = ""
            for wf in db_traits["workflows"]:
                wf_text += f"### {wf['name']} ({wf.get('category', 'general')})\n{wf.get('description', '')}\n"
                if wf.get("nodes"):
                    nodes_text = "\n".join([f"  - {n['node_name']}: {n.get('description', '')}" for n in wf["nodes"]])
                    wf_text += f"Nodes:\n{nodes_text}\n"
                if wf.get("node_order"):
                    wf_text += f"Execution Order: {' -> '.join(wf['node_order'])}\n"
            parts.append(f"## REUSABLE WORKFLOWS\n{wf_text}")

        if db_traits["resources"]:
            res_text = "\n".join([f"- **{r['name']}**: {r.get('description', '')}" for r in db_traits["resources"]])
            parts.append(f"## TOOLS & RESOURCES\n{res_text}")

        return "\n\n---\n\n".join(parts)

    # 2. Fallback to Markdown Seeding
    print(f"[SoulRegistry] Database entry missing. Falling back to Markdown for {resolved_id}")
    
    # Load the shared baseline
    shared_path = Path(__file__).resolve().parent / "souls.md"
    shared_text = ""
    if shared_path.exists():
        shared_text = shared_path.read_text(encoding="utf-8").strip()

    # Load the agent-specific profile
    soul_path = _soul_path_for(resolved_id)
    if not soul_path.exists():
        raise FileNotFoundError(f"Soul file missing for '{resolved_id}': {soul_path}")

    agent_text = soul_path.read_text(encoding="utf-8").strip()
    
    # Combine them
    full_soul = f"{shared_text}\n\n---\n\n{agent_text}" if shared_text else agent_text
    
    if not full_soul.strip():
        raise ValueError(f"Soul content is empty for '{resolved_id}': {soul_path}")
    
    return full_soul
