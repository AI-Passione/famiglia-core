import os
from dotenv import load_dotenv
load_dotenv()
from src.agents.rossini import Rossini
from src.agents.llm.client import client

client.ensure_ollama_ready(auto_pull=False)
rossini = Rossini()
# Force model assignment
client.allocate_resources([rossini])

print("--- Calling Complete Task ---")
resp = rossini.complete_task("greetings", sender="Don Jimmy")
print("\n--- FINAL RESPONSE ---")
print(resp)
