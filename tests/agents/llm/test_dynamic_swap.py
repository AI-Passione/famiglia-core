from famiglia_core.agents.llm.client import client
from unittest.mock import MagicMock

def test_dynamic_swap():
    # Setup test models in config
    print("Testing dynamic model swap...")
    
    # Need to pre-allocate since we check self.allocated_models
    agent1 = MagicMock()
    agent1.name = "test_agent_1"
    agent1.model_config = {"secondary": "phi3:mini", "global_fallback": "gemma3:1b"}
    
    agent2 = MagicMock()
    agent2.name = "test_agent_2"
    agent2.model_config = {"secondary": "codegemma:7b", "global_fallback": "gemma3:1b"}
    
    client.allocate_resources([agent1, agent2])
    
    # 1. Test with first model
    print("\nRequesting from test_agent_1 (should map to phi3:mini)...")
    config1 = {"secondary": "phi3:mini"}
    try:
        res1, model1 = client.complete("Say hello concisely.", config1, "test_agent_1")
        print(f"Success! Model used: {model1}")
    except Exception as e:
        print(f"Error: {e}")
        
    # 2. Test with second model
    print("\nRequesting from test_agent_2 (should map to codegemma:7b)...")
    config2 = {"secondary": "codegemma:7b"}
    try:
        res2, model2 = client.complete("Write a python print hello.", config2, "test_agent_2")
        print(f"Success! Model used: {model2}")
    except Exception as e:
        print(f"Error: {e}")
        
    print("\nCheck output of `ollama ps` to ensure memory is free.")

if __name__ == "__main__":
    test_dynamic_swap()
