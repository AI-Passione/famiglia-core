import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from famiglia_core.agents.llm.client import LLMClient

def test_gemma4_thought_stripping():
    client = LLMClient()
    
    # Input with Gemma 4 thought block
    raw_response = """<|channel>thought
I should check the weather before suggesting a walk. The user is in London.
<channel|>It looks like a great day for a walk in London! The sun is out."""
    
    expected_output = "It looks like a great day for a walk in London! The sun is out."
    
    cleaned = client._clean_ollama_response(raw_response)
    assert cleaned == expected_output

def test_gemma4_no_thinking():
    client = LLMClient()
    
    # Input without thought block
    raw_response = "Hello Don Jimmy, how can I help you today?"
    
    cleaned = client._clean_ollama_response(raw_response)
    assert cleaned == raw_response

def test_gemma4_multiline_stripping():
    client = LLMClient()
    
    # Multiline thought
    raw_response = """<|channel>thought
Line 1 of thinking.
Line 2 of thinking.
<channel|>Final Answer."""
    
    cleaned = client._clean_ollama_response(raw_response)
    assert cleaned == "Final Answer."
