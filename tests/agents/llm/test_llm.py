import sys
from src.agents.llm.client import client
from src.agents.rossini import Rossini

r = Rossini()
q = "could u list out all Github Issues u see?"
mode = "TOOL"
prompt = (
    "--- TOOL TRIGGER RULES ---\n"
    "1. TRIGGER IMMEDIATELY: Output the appropriate [TRIGGER] based on the user request. Do NOT ask for clarification; make reasonable assumptions to trigger the tool.\n"
    "2. NO PLACEHOLDERS: Use only real data from results.\n"
    "3. LANGUAGE: Respond in English.\n\n"
    f"SYSTEM IDENTITY (LITE):\n{r._get_lite_soul(r.soul_profile)}\n\n"
    f"--- AGENT CAPABILITIES ---\n{r.check_capabilities()}\n\n"
    f"User: {q}\nAssistant:"
)

config = {"primary": "qwen2.5:3b-instruct-q4_0"}
print("Prompt length:", len(prompt))
res, model = client.complete(prompt, config, agent_name="Rossini", routing_mode=mode)
print("=== RAW RESPONSE ===")
print(res)
print("====================")
