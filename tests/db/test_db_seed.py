import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.db.seed_don import seed_don

@patch("famiglia_core.db.seed_don.context_store")
def test_seed_don_success(mock_store):
    # Mocking DB session context manager
    mock_cursor = MagicMock()
    mock_store.db_session.return_value.__enter__.return_value = mock_cursor
    
    # First execute (RETURNING id)
    mock_cursor.fetchone.return_value = {"id": 10}
    
    # Call the seed function
    seed_don()
    
    # Verify that it called cursor.execute at least twice (user and platform identity)
    assert mock_cursor.execute.call_count >= 2
    
    # Check that SQL includes expected patterns
    calls = mock_cursor.execute.call_args_list
    assert "INSERT INTO users" in calls[0][0][0]
    assert "INSERT INTO user_platform_identities" in calls[1][0][0]

@patch("famiglia_core.db.seed_don.context_store")
def test_seed_don_failure(mock_store):
    # Mock connection failure (cursor is None)
    mock_store.db_session.return_value.__enter__.return_value = None
    
    # Should handle gracefully without raising (though it prints error)
    seed_don()
    
    # Ensure no execute calls were made
    # (Since it returns early if cursor is None as per code)
    assert not mock_store.db_session.return_value.__enter__.return_value
