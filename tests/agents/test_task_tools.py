import pytest
from unittest.mock import MagicMock, patch
from famiglia_core.agents.orchestration.utils.task_helpers import TaskTools

class MockAgent(TaskTools):
    def __init__(self, name):
        self.name = name
    def propose_action(self, msg):
        return True

@pytest.fixture
def mock_agent():
    return MockAgent("test_agent")

def test_create_scheduled_task_one_off(mock_agent):
    with patch("famiglia_core.agents.orchestration.utils.task_helpers.context_store") as mock_store:
        mock_store.create_scheduled_task.return_value = {"id": 123}
        
        result = mock_agent.create_scheduled_task(
            title="One-off Task",
            task_payload="Do something once"
        )
        
        assert "Successfully created scheduled task #123" in result
        mock_store.create_scheduled_task.assert_called_once()
        mock_store.create_recurring_task.assert_not_called()

def test_create_scheduled_task_recurring(mock_agent):
    with patch("famiglia_core.agents.orchestration.utils.task_helpers.context_store") as mock_store:
        mock_store.create_recurring_task.return_value = {"id": 456}
        
        result = mock_agent.create_scheduled_task(
            title="Daily Task",
            task_payload="Do something daily",
            schedule_config={"interval_minutes": 1440}
        )
        
        assert "Successfully created recurring task #456" in result
        mock_store.create_recurring_task.assert_called_once()
        mock_store.create_scheduled_task.assert_not_called()
