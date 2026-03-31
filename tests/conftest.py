import os
import pytest
from unittest.mock import MagicMock, patch

# --- Set environment variables for tests ---
os.environ["DUCKDB_DWH_PATH"] = "/tmp/test_duckdb_dwh.db"
os.environ["UPLOAD_DIR"] = "/tmp/test_uploads"
os.environ["USER_SLACK_ID"] = "U_TEST_ID"

@pytest.fixture(autouse=True)
def mock_duckdb_tool():
    """
    Globally mock duckdb_tool to prevent file system operations during tests.
    """
    with patch("famiglia_core.agents.tools.duckdb.duckdb_tool") as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_context_store_pool():
    """
    Prevent Real Database Connection Pool from initializing.
    """
    with patch("famiglia_core.db.agents.context_store.pool.SimpleConnectionPool") as mock:
        yield mock
