import pytest
from unittest.mock import patch
from famiglia_core.agents.riccado import Riccado

# client.complete() is called TWICE per complete_task:
# 1. by _get_routing_mode (returns classification like "COMPLEX")
# 2. by the actual task completion
_ROUTING_RETURN = ("COMPLEX", "ollama-gemma3")


@patch('famiglia_core.agents.base_agent.client.complete')
def test_riccado_initialization(mock_complete):
    riccado = Riccado()
    assert riccado.name == "Riccado"
    assert "Data Engineer" in riccado.role or "engineer" in riccado.role.lower()
    assert riccado.model_config["primary"] == "claude-3.7-sonnet"
    assert riccado.model_config["global_fallback"] == "ollama-gemma3"


@patch('famiglia_core.agents.base_agent.client.complete')
def test_review_code(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("MA CHE CAZZO! This loop is N+1 dog shit. Use a JOIN instead.", "claude-3.7-sonnet")]
    riccado = Riccado()
    result = riccado.review_code("for user in users: db.query(user.id)")
    assert result is not None


@patch('famiglia_core.agents.base_agent.client.complete')
def test_write_pipeline(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("-- dbt model: stg_orders\nSELECT id, amount FROM raw.orders", "claude-3.7-sonnet")]
    riccado = Riccado()
    result = riccado.write_pipeline("Aggregate daily orders by region")
    assert result is not None


@patch('famiglia_core.agents.base_agent.client.complete')
def test_debug_query(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("SELECT * is CRIMINAL. Use explicit columns!", "claude-3.7-sonnet")]
    riccado = Riccado()
    result = riccado.debug_query("SELECT * FROM orders WHERE 1=1")
    assert result is not None


@patch('famiglia_core.agents.base_agent.client.complete')
def test_infra_check(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("Redis is not persistent. Enable AOF or you lose data, idiota!", "claude-3.7-sonnet")]
    riccado = Riccado()
    result = riccado.infra_check("redis")
    assert result is not None


@patch('famiglia_core.agents.base_agent.client.complete')
def test_deploy(mock_complete):
    mock_complete.side_effect = [_ROUTING_RETURN, ("Deployed passione-api v2.1.0. Run smoke tests. È fatto!", "claude-3.7-sonnet")]
    riccado = Riccado()
    result = riccado.deploy("passione-api")
    assert result is not None
