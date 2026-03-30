import os
import sys
import re
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path to allow imports from src
# For src/db/agents/migrate_souls_to_db.py: 
# .parent(agents) -> .parent(db) -> .parent(src) -> .parent(root)
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from src.agents.souls.soul_registry import SOUL_REGISTRY

def parse_soul_md(content: str):
    """
    Parses a soul Markdown file into rigid sections.
    """
    sections = {
        "persona": [],
        "reply_constraints": [],
        "identity": [],
        "skills": [],
        "tools": [],
        "resources": [],
        "workflow": []
    }
    
    current_section = "persona" # Default to persona for intro text
    lines = content.splitlines()
    
    # Mapping of Markdown headers to schema columns
    header_map = {
        r"PERSONA.*TONE": "persona",
        r"REPLY.*CONSTRAINTS": "reply_constraints",
        r"PHRASES.*IDENTITY": "identity",
        r"SPECIALIZED.*SKILLS": "skills",
        r"TOOLS.*RESOURCES": "tools_resources", # special case
        r"TOOLS": "tools",
        r"RESOURCES": "resources",
        r"WORKFLOW": "workflow",
        r"TOOL.*MASTER": "tools",
        r"SEARCH.*MASTER": "tools",
        r"REUSABLE.*WORKFLOWS": "workflow",
        r"DOMAIN.*TRIGGERS": "tools"
    }

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("##"):
            # New header found
            header_text = re.sub(r"^#+\s*", "", stripped_line).upper()
            found_match = False
            for pattern, section_key in header_map.items():
                if re.search(pattern, header_text):
                    if section_key == "tools_resources":
                        current_section = "tools" # We'll just put it in tools for now, or split if needed
                    else:
                        current_section = section_key
                    found_match = True
                    break
            # If no match found, we append to current section or default back to persona?
            # Actually, if it's a new header we don't recognize, we should probably still include it
            # But where? Let's just keep appending to current_status if found_match is False
        
        sections[current_section].append(line)

    # Join lines back into strings
    return {k: "\n".join(v).strip() for k, v in sections.items()}

def migrate_souls():
    load_dotenv()
    
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "passione_admin"),
        "password": os.getenv("DB_PASSWORD", "passione_password"),
        "dbname": os.getenv("DB_NAME", "passione_db")
    }
    
    souls_dir = project_root / "src" / "agents" / "souls"
    shared_soul_path = souls_dir / "souls.md"
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Migrate shared baseline
        if shared_soul_path.exists():
            print(f"Migrating shared baseline from {shared_soul_path}...")
            content = shared_soul_path.read_text(encoding="utf-8").strip()
            
            cursor.execute("""
                INSERT INTO shared_soul_baseline (id, content, updated_at)
                VALUES (1, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = NOW();
            """, (content,))
            print("Shared baseline migrated.")
        
        # 2. Migrate agent souls
        for agent_id, config in SOUL_REGISTRY.items():
            agent_file = souls_dir / f"{agent_id}.md"
            if agent_file.exists():
                print(f"Migrating soul for agent '{agent_id}' from {agent_file}...")
                content = agent_file.read_text(encoding="utf-8").strip()
                parsed_sections = parse_soul_md(content)
                
                agent_name = agent_id.capitalize()
                aliases = config.get("aliases", [])
                
                cursor.execute("""
                    INSERT INTO agent_souls (
                        agent_id, agent_name, aliases, 
                        persona, reply_constraints, identity, 
                        skills, tools, resources, workflow, 
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (agent_id) DO UPDATE SET
                        agent_name = EXCLUDED.agent_name,
                        aliases = EXCLUDED.aliases,
                        persona = EXCLUDED.persona,
                        reply_constraints = EXCLUDED.reply_constraints,
                        identity = EXCLUDED.identity,
                        skills = EXCLUDED.skills,
                        tools = EXCLUDED.tools,
                        resources = EXCLUDED.resources,
                        workflow = EXCLUDED.workflow,
                        updated_at = NOW();
                """, (
                    agent_id, agent_name, aliases,
                    parsed_sections["persona"],
                    parsed_sections["reply_constraints"],
                    parsed_sections["identity"],
                    parsed_sections["skills"],
                    parsed_sections["tools"],
                    parsed_sections["resources"],
                    parsed_sections["workflow"]
                ))
                print(f"Soul for '{agent_id}' migrated and parsed.")
            else:
                print(f"Warning: Soul file for agent '{agent_id}' not found at {agent_file}")
        
        conn.commit()
        print("Migration and parsing completed successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()

if __name__ == "__main__":
    migrate_souls()
