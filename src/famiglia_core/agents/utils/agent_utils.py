import re
from typing import Any, Dict, List, Optional

def normalize_task_for_routing(task: str) -> str:
    """Normalize task text for routing purposes."""
    text = (task or "").strip()
    # Handle Slack mention forms: <@U123...> and <@U123...|display-name>
    text = re.sub(r"<@[A-Za-z0-9]+(?:\|[^>]+)?>", "", text)
    text = text.strip().lower()
    return text.strip("!?.:,;-")

def is_idle_task(agent_name: str, task: str) -> bool:
    """Check if the task is an idle state message."""
    normalized = normalize_task_for_routing(task)
    if not normalized:
        return True
    return normalized in {agent_name.lower(), f"@{agent_name.lower()}"}

def build_conversation_key(sender: str, conversation_key: Optional[str]) -> str:
    """Build a unique conversation key for storage."""
    if conversation_key:
        return conversation_key[:255]
    safe_sender = (sender or "unknown").replace(" ", "_")
    return f"default:{safe_sender}"[:255]

def truncate(value: str, limit: int) -> str:
    """Truncate a string to a specific limit."""
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."

def format_recent_messages(messages: List[Dict[str, Any]]) -> str:
    """Format recent messages for prompt inclusion."""
    if not messages:
        return "- None"
    lines = []
    for message in messages:
        role = str(message.get("role") or "unknown").upper()
        sender = message.get("sender")
        content = truncate((message.get("content") or "").replace("\n", " "), 280)
        label = f"{role} ({sender})" if sender else role
        lines.append(f"- {label}: {content}")
    return "\n".join(lines)

def format_memories(memories: List[Dict[str, Any]]) -> str:
    """Format memories for prompt inclusion."""
    if not memories:
        return "- None"
    lines = []
    for memory in memories:
        key = memory.get("memory_key", "unknown")
        value = truncate(memory.get("memory_value", ""), 180)
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)

def extract_model_size_billions(client: Any, model_name: str) -> Optional[str]:
    """Identify and format model size from model string."""
    candidates = [model_name]
    if model_name.startswith(("ollama-", "remote-ollama-")):
        try:
            candidates.append(client._ollama_model_from_name(model_name))
        except Exception:
            pass

    for candidate in candidates:
        match = re.search(r"(\d+(?:\.\d+)?)b\b", candidate.lower())
        if not match:
            continue
        size = match.group(1)
        if "." in size:
            size = size.rstrip("0").rstrip(".")
        return f"{size}B"
    return None

def get_lite_soul(agent_name: str, agent_role: str, soul_profile: str) -> str:
    """Extract essential personality sections to keep the agent's voice even in 'Lite' mode."""
    lite_parts = []
    sections_to_keep = [
        "## PERSONA & TONE", 
        "## PHRASES & IDENTITY", 
        "## REPLY CONSTRAINTS", 
        "## DOMAIN TRiggers (Anti-Confusion)",
        "## NOTION TOOL MASTER",
        "## GITHUB TOOL MASTER",
        "## REUSABLE WORKFLOWS"
    ]
    
    current_section = None
    lines = soul_profile.split('\n')
    for line in lines:
        if line.startswith('## '):
            current_section = line.strip()
        
        if current_section in sections_to_keep:
            lite_parts.append(line)
    
    return "\n".join(lite_parts) if lite_parts else f"You are {agent_name}, {agent_role}."
