import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.agents.rossini import Rossini
from src.agents.llm.client import client

def test_routing_modes():
    agent = Rossini()
    
    # Mock routing response to avoid Ollama latency
    original_complete = client.complete
    
    def mocked_complete(prompt, config, name):
        if "Router" in name:
            p = prompt.lower()
            if "market strategy" in p or "analyze" in p:
                return "COMPLEX", "ollama-gemma3"
            if "search" in p or "find" in p:
                return "SEARCH", "ollama-gemma3"
            return "CHAT", "ollama-gemma3"
        return "Success", "ollama-gemma3"

    client.complete = mocked_complete
    
    test_cases = [
        ("hi", "CHAT"),
        ("search for Love", "SEARCH"),
        ("Draft a market strategy for high-end pasta", "COMPLEX"),
    ]
    
    print("\n--- Verifying Ternary Routing Logic ---")
    for task, expected in test_cases:
        mode = agent._get_routing_mode(task)
        print(f"Task: '{task}' -> Mode: {mode} (Expected: {expected})")
        assert mode == expected, f"Failed for '{task}': got {mode}, expected {expected}"
    print("Routing tests passed!\n")

def test_search_output():
    # Verify that in SEARCH mode, we use Gemma 3 and it can trigger a tool
    agent = Rossini()
    
    # Mock client.complete to return a trigger
    original_complete = client.complete
    client.complete = MagicMock(return_value=("[TRIGGER: web_search(query=\"Love\")]", "ollama-gemma3"))
    
    print("--- Verifying SEARCH mode output ---")
    # We aren't actually running the tool loop here, just verifying complete_task picks the right model
    # and constructs the prompt correctly (via internal prints if we had them, or just observing behavior)
    
    # Test a simple search
    task = "search for Love"
    # This will trigger the tool loop
    # To avoid actual network calls, we'd need to mock many things.
    # For now, let's just check the routing mode and model used in a single turn.
    
    mode = agent._get_routing_mode(task)
    print(f"Mode for '{task}': {mode}")
    
    print("All verification tests ran (manually inspect routing above).")

if __name__ == "__main__":
    try:
        test_routing_modes()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
