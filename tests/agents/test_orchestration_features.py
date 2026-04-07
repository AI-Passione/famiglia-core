import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.orchestration.features.market_research.market_research import MarketResearchWorkflow, MarketResearchState
from famiglia_core.agents.orchestration.features.product_development.prd_drafting import PRDDraftingWorkflow, PRDDraftingState

# --- Fixtures ---

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.name = "TestRossini"
    agent.model_config = {"primary": "test-model"}
    agent.get_model_config.return_value = {"primary": "test-model"}
    return agent

@pytest.fixture
def mock_llm():
    # Patch the LLMClient class directly to be more robust
    with patch("famiglia_core.agents.llm.client.LLMClient.complete") as mock_complete:
        # Default return value is a tuple to prevent unpacking errors
        mock_complete.return_value = ("default response", "default-model")
        yield mock_complete

@pytest.fixture
def mock_services():
    with patch("famiglia_core.agents.orchestration.features.market_research.market_research.intelligence_service") as mock_intel_research, \
         patch("famiglia_core.agents.orchestration.features.product_development.prd_drafting.intelligence_service") as mock_intel_prd, \
         patch("famiglia_core.agents.orchestration.features.market_research.market_research.slack_queue") as mock_slack_research, \
         patch("famiglia_core.agents.orchestration.features.product_development.prd_drafting.slack_queue") as mock_slack_prd, \
         patch("famiglia_core.agents.orchestration.features.market_research.market_research.web_search_client") as mock_search:
        yield {
            "intel_research": mock_intel_research,
            "intel_prd": mock_intel_prd,
            "slack_research": mock_slack_research,
            "slack_prd": mock_slack_prd,
            "search": mock_search
        }

# --- Market Research Tests ---

def test_market_research_perform_search(mock_agent, mock_llm, mock_services):
    workflow = MarketResearchWorkflow(mock_agent)
    
    mock_services["search"].search.return_value = "Search results"
    
    state = MarketResearchState(task="Research AI agents", research_topic="AI", search_results="", curated_markdown="", notion_page_id="", notion_url="", business_ideas="", slack_channel="")
    new_state = workflow.perform_search(state)
    
    assert new_state["search_success"] is True
    assert new_state["search_results"] == "Search results"

def test_market_research_save_to_intel(mock_agent, mock_services):
    workflow = MarketResearchWorkflow(mock_agent)
    state = MarketResearchState(
        task="Test", 
        research_topic="AI", 
        curated_markdown="# AI Research", 
        business_ideas="Idea 1",
        search_results="", notion_page_id="", notion_url="", slack_channel=""
    )
    
    workflow.save_to_intelligence(state) # Corrected name
    
    # Verify intelligence service was called
    assert mock_services["intel_research"].create_item.called
    call_args = mock_services["intel_research"].create_item.call_args[0][0]
    assert call_args.title == "Market Research: AI"
    assert "# AI Research" in call_args.content

# --- PRD Drafting Tests ---

def test_prd_drafting_understand_context(mock_agent, mock_llm):
    workflow = PRDDraftingWorkflow(mock_agent)
    
    # Corrected usage: mock_llm is now the direct mock
    mock_llm.return_value = ("SUBJECT: Jimwurst\nCONTEXT: A sausage delivery app\nTITLE: Jimwurst MVP", "test-model")
    
    state = PRDDraftingState(
        task="Create a PRD for Jimwurst sausage delivery",
        product_subject="", product_context="", prd_title="",
        notion_intelligence="", notion_summary="", github_intelligence="", github_summary="",
        web_intelligence="", web_summary="", synthesis="", prd_markdown="",
        notion_page_id="", notion_url="", slack_channel="", retry_count=0, last_error="", notion_success=False
    )
    
    updates = workflow.understand_context(state) # This node returns a dict of updates
    
    assert updates["product_subject"] == "Jimwurst"
    assert "sausage delivery" in updates["product_context"]
    assert updates["prd_title"] == "Jimwurst MVP"

def test_prd_drafting_synthesis(mock_agent, mock_llm):
    workflow = PRDDraftingWorkflow(mock_agent)
    
    mock_llm.return_value = ("# PRD Content\nOptimized Synthesis", "test-model")
    
    state = PRDDraftingState(
        task="Test PRD", prd_title="Test App", product_subject="Test", product_context="Context",
        web_intelligence="Web data", notion_intelligence="Notion data", github_intelligence="Git data",
        notion_summary="", github_summary="", web_summary="", synthesis="", prd_markdown="",
        notion_page_id="", notion_url="", slack_channel="", retry_count=0, last_error="", notion_success=False
    )
    
    # Correct method name is 'synthesize'
    new_state = workflow.synthesize(state)
    assert "Optimized Synthesis" in new_state["synthesis"]

def test_full_market_research_graph(mock_agent, mock_llm, mock_services):
    # Synchronous graph test
    
    from famiglia_core.agents.orchestration.features.market_research.market_research import setup_market_research_graph
    from langgraph.checkpoint.memory import MemorySaver # Use real in-memory saver
    
    # Patch PostgresCheckpointer to return a MemorySaver instead of a MagicMock
    with patch("famiglia_core.agents.orchestration.features.market_research.market_research.PostgresCheckpointer", return_value=MemorySaver()):
        graph = setup_market_research_graph(mock_agent)
        
        # Setup LLM mocks for the sequence using the direct mock_llm
        mock_llm.side_effect = [
            ("# Curated Markdown", "model"),             # curate_results
            ("BUSINESS IDEAS: Idea 1", "model"),         # generate_ideas
            ("SUMMARY: Done", "model"),                  # notify_slack (if needed)
        ]
        
        # Mock search results
        mock_services["search"].search.return_value = "Some web results"
        
        initial_state = {
            "task": "Research AI agents",
            "research_topic": "AI",
            "search_results": "",
            "curated_markdown": "",
            "notion_page_id": "",
            "notion_url": "",
            "business_ideas": "",
            "slack_channel": "test-channel",
            "retry_count": 0,
            "search_retry_count": 0,
            "last_error": "",
            "notion_success": False,
            "search_success": False,
            "search_query": ""
        }
        
        # graph.invoke is synchronous
        result = graph.invoke(initial_state, {"configurable": {"thread_id": "test"}})
        
        assert result["research_topic"] == "AI"
        assert result["search_success"] is True
        assert mock_services["intel_research"].create_item.called
