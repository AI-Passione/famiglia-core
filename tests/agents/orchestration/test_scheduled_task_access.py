from famiglia_core.agents.alfredo import Alfredo
from famiglia_core.agents.vito import Vito


def test_all_agents_can_create_scheduled_tasks():
    vito = Vito()
    assert "create_scheduled_task" in vito.tools
    assert "enqueue_batched_task" in vito.tools


def test_only_alfredo_has_scheduled_task_status_tools_registered():
    vito = Vito()
    alfredo = Alfredo()

    assert "list_scheduled_tasks" not in vito.tools
    assert "list_batched_tasks" not in vito.tools
    assert "get_scheduled_tasks_status" not in vito.tools

    assert "list_scheduled_tasks" in alfredo.tools
    assert "list_batched_tasks" in alfredo.tools
    assert "get_scheduled_tasks_status" in alfredo.tools


def test_non_alfredo_is_blocked_from_global_scheduled_task_status():
    vito = Vito()
    response = vito.list_scheduled_tasks_tool()
    assert "Permission denied" in response
