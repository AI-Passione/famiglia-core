import pytest
from unittest.mock import patch, MagicMock, call
from src.agents.vito import Vito
from src.agents.bella import Bella

# client.complete() is called TWICE per complete_task:
# 1. by _get_routing_mode (returns classification like "COMPLEX")
# 2. by the actual task completion
_ROUTING_RETURN = ("COMPLEX", "ollama-gemma3")

@patch('src.agents.base_agent.client.complete')
def test_vito_initialization(mock_complete):
    vito = Vito()
    assert vito.name == "Vito"
    assert "Finance" in vito.role or "finance" in vito.role
    assert vito.model_config["primary"] == "perplexity-sonar-pro"

@patch('src.agents.base_agent.client.complete')
def test_bella_initialization(mock_complete):
    bella = Bella()
    assert bella.name == "Bella"
    assert "Notion" in bella.role or "administration" in bella.role.lower() or "scheduling" in bella.role.lower()
    assert bella.model_config["primary"] == "gemini-2.0-flash"

@patch('src.agents.base_agent.client.complete')
def test_vito_review_expense(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("Expense is justified.", "gemini-2.0-flash")]
    vito = Vito()
    result = vito.review_expense(50.0, "Lunch")
    assert result is not None

@patch('src.agents.base_agent.client.complete')
def test_bella_schedule_meeting(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("Meeting scheduled.", "gemini-2.0-flash")]
    bella = Bella()
    result = bella.schedule_meeting("Sync at 10am")
    assert result is not None
