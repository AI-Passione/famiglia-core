import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.orchestration.scheduling_supervisor import SchedulingMasterSupervisor
from famiglia_core.agents.orchestration.utils.state import AgentState

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.name = "TestSupervisor"
    agent.soul_profile = "You are a test supervisor."
    agent.model_config = {"primary": "test-model"}
    return agent

@pytest.fixture
def mock_worker_graphs():
    with patch("famiglia_core.agents.orchestration.scheduling_supervisor.setup_prd_drafting_graph") as mock_prd_draft, \
         patch("famiglia_core.agents.orchestration.scheduling_supervisor.setup_prd_review_graph") as mock_prd_rev, \
         patch("famiglia_core.agents.orchestration.scheduling_supervisor.setup_milestone_creation_graph") as mock_milestone, \
         patch("famiglia_core.agents.orchestration.scheduling_supervisor.setup_market_research_graph") as mock_market:
        yield {
            "prd_draft": mock_prd_draft,
            "prd_rev": mock_prd_rev,
            "milestone": mock_milestone,
            "market": mock_market
        }

def test_supervisor_routing_logic(mock_agent, mock_worker_graphs):
    # Mock PostgresCheckpointer to avoid DB connection
    with patch("famiglia_core.agents.orchestration.scheduling_supervisor.PostgresCheckpointer"):
        supervisor = SchedulingMasterSupervisor(mock_agent)
        
        # 1. Test market research routing
        state = AgentState(metadata={"task_record": {"metadata": {"task_type": "market_research"}}})
        new_state = supervisor._route_to_worker(state)
        assert new_state["routing_mode"] == "market_research"
        
        # 2. Test PRD drafting routing
        state = AgentState(metadata={"task_record": {"metadata": {"task_type": "prd_drafting"}}})
        new_state = supervisor._route_to_worker(state)
        assert new_state["routing_mode"] == "prd_drafting"
        
        # 3. Test handle both object and dict (as per code)
        mock_task_obj = MagicMock()
        mock_task_obj.task_type = "prd_review_autoscan"
        state = AgentState(metadata={"task_record": mock_task_obj})
        new_state = supervisor._route_to_worker(state)
        assert new_state["routing_mode"] == "prd_review"
        
        # 4. Test fallback to support
        state = AgentState(metadata={})
        new_state = supervisor._route_to_worker(state)
        assert new_state["routing_mode"] == "support"

def test_supervisor_delegation_calls(mock_agent, mock_worker_graphs):
    with patch("famiglia_core.agents.orchestration.scheduling_supervisor.PostgresCheckpointer"):
        supervisor = SchedulingMasterSupervisor(mock_agent)
        
        # Mock the market research graph's invoke method
        mock_market_graph = mock_worker_graphs["market"].return_value
        mock_market_graph.invoke.return_value = {"final_response": "Market report done"}
        
        state = AgentState(conversation_key="test_conv")
        new_state = supervisor.call_market_research(state)
        
        assert mock_market_graph.invoke.called
        assert new_state["final_response"] == "Market report done"

def test_supervisor_handle_support(mock_agent, mock_worker_graphs):
    with patch("famiglia_core.agents.orchestration.scheduling_supervisor.PostgresCheckpointer"):
        supervisor = SchedulingMasterSupervisor(mock_agent)
        
        with patch("famiglia_core.agents.llm.client.LLMClient.complete") as mock_complete:
            mock_complete.return_value = ("Support response", "model-size")
            
            state = AgentState(task="How are you?", model_to_use="large")
            new_state = supervisor.handle_support(state)
            
            assert new_state["final_response"] == "Support response"
            assert new_state["used_model"] == "model-size"
            
            # Verify it used the model from state
            call_config = mock_complete.call_args[0][1]
            assert call_config["primary"] == "large"
