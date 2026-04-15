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

def test_market_research_curate_results(mock_agent, mock_llm):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_llm.return_value = ("# Curated Report", "model")
    
    state = MarketResearchState(
        task="Research AI",
        research_topic="AI",
        search_results="Some results",
        curated_markdown="",
        notion_page_id="", notion_url="", business_ideas="", slack_channel=""
    )
    
    new_state = workflow.curate_results(state)
    assert new_state["curated_markdown"] == "# Curated Report"
    assert mock_llm.called

def test_market_research_save_to_intel_failure(mock_agent, mock_services):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_services["intel_research"].create_item.side_effect = Exception("DB Timeout")
    
    state = MarketResearchState(
        task="Test", 
        research_topic="AI", 
        curated_markdown="# AI Research", 
        business_ideas="Idea 1",
        search_results="", notion_page_id="", notion_url="", slack_channel=""
    )
    
    new_state = workflow.save_to_intelligence(state)
    assert new_state["db_success"] is False
    assert "DB Timeout" in new_state["last_error"]
    assert "FAILED" in new_state["final_response"]

def test_market_research_generate_ideas(mock_agent, mock_llm):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_llm.return_value = ("### Business Ideas\n1. AI Assistant", "model")
    
    state = MarketResearchState(
        task="Research AI",
        research_topic="AI",
        curated_markdown="# AI Research",
        business_ideas="",
        search_results="", notion_page_id="", notion_url="", slack_channel=""
    )
    
    new_state = workflow.generate_ideas(state)
    assert "AI Assistant" in new_state["business_ideas"]

def test_market_research_load_personality(mock_agent):
    from unittest.mock import mock_open
    workflow = MarketResearchWorkflow(mock_agent)
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="## PERSONA & TONE\nDr. Rossini is a strategist.")):
        personality = workflow._load_rossini_personality()
        assert "Dr. Rossini is a strategist" in personality

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

def test_market_research_extract_research_goal(mock_agent):
    workflow = MarketResearchWorkflow(mock_agent)
    
    # 1. Situation Room format
    assert workflow._extract_research_goal("Task... Client Specification: AI Agents") == "AI Agents"
    
    # 2. Boilerplate format
    assert workflow._extract_research_goal("Executing graph market_research Quantum Computing") == "Quantum Computing"
    
    # 3. Fallback
    assert workflow._extract_research_goal("Just a topic") == "Just a topic"
    assert workflow._extract_research_goal("") == "General Market Research"

def test_market_research_refine_search_query(mock_agent, mock_llm):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_llm.return_value = ("refined query", "model")
    
    state = MarketResearchState(
        research_topic="AI", 
        last_error="No results",
        search_query="AI",
        search_retry_count=0,
        task="Research AI",
        search_results="", curated_markdown="", notion_page_id="", notion_url="", business_ideas="", slack_channel=""
    )
    
    new_state = workflow.refine_search_query(state)
    
    assert new_state["search_query"] == "refined query"
    assert new_state["search_retry_count"] == 1

def test_market_research_perform_search_failure(mock_agent, mock_services):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_services["search"].search.side_effect = Exception("Search API Down")
    
    state = MarketResearchState(
        task="Test", 
        research_topic="AI",
        search_results="", curated_markdown="", notion_page_id="", notion_url="", business_ideas="", slack_channel=""
    )
    
    new_state = workflow.perform_search(state)
    
    assert new_state["search_success"] is False
    assert "Search API Down" in new_state["last_error"]

def test_market_research_deliver_results(mock_agent, mock_llm, mock_services):
    workflow = MarketResearchWorkflow(mock_agent)
    mock_llm.return_value = ("### Ideas\n- **Idea 1**: [Link](http://test.com)", "model")

    state = MarketResearchState(
        research_topic="AI",
        business_ideas="Some ideas",
        db_success=True,
        slack_channel="C123",
        task="Research AI",
        search_results="", curated_markdown="", notion_page_id="", notion_url="", search_retry_count=0
    )

    new_state = workflow.deliver_results(state)

    assert mock_services["slack_research"].post_message.called
    msg = mock_services["slack_research"].post_message.call_args[1]["message"]
    # Check Markdown → Slack mrkdwn conversions
    assert "*Ideas*" in msg
    assert "*Idea 1*" in msg
    assert "<http://test.com|Link>" in msg
    # Check final_response is set for Directive Terminal
    assert "final_response" in new_state
    assert "AI" in new_state["final_response"]


def test_market_research_extract_research_goal_autonomous_queue(mock_agent):
    """Autonomous queue wraps the real topic with metadata — ensure it is stripped."""
    workflow = MarketResearchWorkflow(mock_agent)

    task = "love\n\nTask metadata:\n- No extra metadata provided.\n\nExecution constraints:\n- Provide concise execution output."
    assert workflow._extract_research_goal(task) == "love"

    task2 = "AI Trends 2025\n\nExecution constraints:\n- This task is running from the autonomous scheduled queue."
    assert workflow._extract_research_goal(task2) == "AI Trends 2025"


# --- Web Search Tests ---

def test_web_search_uses_env_key():
    """When OLLAMA_API_KEY env var is set it should be used directly."""
    from famiglia_core.agents.tools.web_search import WebSearchClient
    with patch.dict("os.environ", {"OLLAMA_API_KEY": "env-key-123"}):
        client = WebSearchClient()
        assert client._resolve_api_key() == "env-key-123"


def test_web_search_falls_back_to_db_key():
    """When env var is absent the key should be fetched from user_connections table."""
    from famiglia_core.agents.tools.web_search import WebSearchClient
    with patch.dict("os.environ", {}, clear=True):
        client = WebSearchClient()
        # Patch the store at the module level where it is imported inside the method
        with patch("famiglia_core.db.tools.user_connections_store.user_connections_store.get_connection") as mock_get:
            mock_get.return_value = {"access_token": "db-key-456"}
            key = client._resolve_api_key()
        assert key == "db-key-456"


def test_web_search_returns_error_when_no_key():
    """If neither env var nor DB provides a key, search() returns the expected error string."""
    from famiglia_core.agents.tools.web_search import WebSearchClient
    with patch.dict("os.environ", {}, clear=True):
        client = WebSearchClient()
        with patch("famiglia_core.db.tools.user_connections_store.user_connections_store.get_connection", return_value=None):
            result = client.search("test query")
    assert "OLLAMA_API_KEY is not set" in result


def test_web_search_uses_db_key_for_request():
    """End-to-end: key from DB is used in the Authorization header."""
    from famiglia_core.agents.tools.web_search import WebSearchClient
    import urllib.request

    with patch.dict("os.environ", {}, clear=True):
        client = WebSearchClient()
        with patch("famiglia_core.db.tools.user_connections_store.user_connections_store.get_connection",
                   return_value={"access_token": "db-key-789"}), \
             patch("famiglia_core.db.agents.context_store.context_store.get_web_search_cache", return_value=None), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"results": [{"title": "T", "url": "http://x.com", "content": "c"}]}'
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            with patch("famiglia_core.db.agents.context_store.context_store.set_web_search_cache"):
                client.search("test query")

        called_req = mock_urlopen.call_args[0][0]
        assert called_req.get_header("Authorization") == "Bearer db-key-789"


def test_web_search_cache_hit():
    from famiglia_core.agents.tools.web_search import WebSearchClient
    with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-key"}):
        client = WebSearchClient()
        
        with patch("famiglia_core.db.agents.context_store.context_store.get_web_search_cache") as mock_get, \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_get.return_value = [{"title": "Cached", "url": "http://cached.com", "content": "data"}]
            
            result = client.search("test query")
            
            assert "Cached" in result
            mock_urlopen.assert_not_called()

def test_web_search_http_error():
    from famiglia_core.agents.tools.web_search import WebSearchClient
    import urllib.error
    with patch.dict("os.environ", {"OLLAMA_API_KEY": "key"}):
        client = WebSearchClient()
        
        with patch("famiglia_core.db.agents.context_store.context_store.get_web_search_cache", return_value=None), \
             patch("urllib.request.urlopen") as mock_urlopen:
            
            # Mock HTTPError
            import urllib.request
            mock_urlopen.side_effect = urllib.error.HTTPError("http://ollama.com", 500, "Internal Server Error", {}, None)
            
            result = client.search("test query")
            assert "HTTP 500" in result

def test_web_search_format_results():
    from famiglia_core.agents.tools.web_search import WebSearchClient
    client = WebSearchClient()
    results = [{"title": "T1", "url": "U1", "content": "C1"}]
    formatted = client._format_results("query", results)
    assert "T1" in formatted
    assert "U1" in formatted
    assert "C1" in formatted
