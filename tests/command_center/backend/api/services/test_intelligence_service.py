import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.command_center.backend.api.services.intelligence_service import IntelligenceService
from famiglia_core.command_center.backend.api.models.intelligence import IntelligenceItemCreate, IntelligenceItemUpdate

@pytest.fixture
def mock_db():
    with patch("famiglia_core.command_center.backend.api.services.intelligence_service.context_store") as mock_store:
        mock_cursor = MagicMock()
        # Mock context_store.db_session() context manager
        mock_store.db_session.return_value.__enter__.return_value = mock_cursor
        yield {"store": mock_store, "cursor": mock_cursor}

def test_intelligence_service_list_items(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].fetchall.return_value = [{"id": 1, "title": "Test"}]
    
    items = service.list_items(item_type="market_research")
    
    assert len(items) == 1
    assert items[0]["title"] == "Test"
    # Verify SQL filter
    executed_sql = mock_db["cursor"].execute.call_args[0][0]
    assert "WHERE item_type = %s" in executed_sql

def test_intelligence_service_get_item(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].fetchone.return_value = {"id": 1, "title": "Test"}
    
    item = service.get_item(1)
    assert item["id"] == 1
    mock_db["cursor"].execute.assert_called_with("SELECT * FROM intelligence_items WHERE id = %s", (1,))

def test_intelligence_service_create_item(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].fetchone.return_value = {"id": 100, "title": "New Item"}
    
    new_item = IntelligenceItemCreate(
        title="New Item",
        content="Content",
        summary="Summary",
        status="Completed",
        item_type="market_research",
        metadata={"key": "value"}
    )
    
    row = service.create_item(new_item)
    assert row["id"] == 100
    assert mock_db["cursor"].execute.called
    # Verify metadata serialization
    mock_db["store"]._safe_json.assert_called_with({"key": "value"})

def test_intelligence_service_update_item(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].fetchone.return_value = {"id": 1, "title": "Updated"}
    
    update = IntelligenceItemUpdate(title="Updated")
    row = service.update_item(1, update)
    
    assert row["title"] == "Updated"
    executed_sql = mock_db["cursor"].execute.call_args[0][0]
    assert "UPDATE intelligence_items" in executed_sql
    assert "title = %s" in executed_sql

def test_intelligence_service_delete_item(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].rowcount = 1
    
    success = service.delete_item(1)
    assert success is True
    mock_db["cursor"].execute.assert_called_with("DELETE FROM intelligence_items WHERE id = %s", (1,))

def test_intelligence_service_list_items_error_handling(mock_db):
    service = IntelligenceService()
    mock_db["cursor"].execute.side_effect = Exception("DB Error")
    
    items = service.list_items()
    assert items == []
