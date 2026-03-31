from unittest.mock import MagicMock, patch

from src.db.context_store import AgentContextStore


def test_log_message_persists_with_conversation_scope():
    with patch("src.db.context_store.psycopg2.connect") as mock_connect:
        conn_conversation = MagicMock()
        conn_message = MagicMock()
        mock_connect.side_effect = [conn_conversation, conn_message]

        conversation_cursor = conn_conversation.cursor.return_value
        message_cursor = conn_message.cursor.return_value
        conversation_cursor.fetchone.return_value = (11,)
        message_cursor.fetchone.return_value = (22,)

        store = AgentContextStore()
        message_id = store.log_message(
            agent_name="Alfredo",
            conversation_key="slack:C123:171234.1000:U111",
            role="user",
            content="Status update?",
            sender="Don Jimmy",
        )

        assert message_id == 22
        conv_sql, conv_params = conversation_cursor.execute.call_args_list[0][0]
        assert "agent_conversations" in conv_sql
        # Conversations are now shared by conversation_key only (no agent_name)
        assert conv_params[0] == "slack:C123:171234.1000:U111"

        msg_sql, msg_params = message_cursor.execute.call_args_list[0][0]
        assert "agent_messages" in msg_sql
        assert msg_params[0] == 11  # conversation_id
        assert msg_params[1] == "Alfredo"  # agent_name (processing agent)
        assert msg_params[3] == "user"  # role
        assert msg_params[4] == "Status update?"  # content


def test_get_recent_messages_is_filtered_by_conversation():
    with patch("src.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        mock_connect.return_value = conn

        cursor = conn.cursor.return_value
        cursor.fetchall.return_value = [
            {"role": "assistant", "content": "All good.", "sender": "Alfredo"},
            {"role": "user", "content": "How are things?", "sender": "Don Jimmy"},
        ]

        store = AgentContextStore()
        rows = store.get_recent_messages(
            conversation_key="slack:C123:171234.1000:U111",
            limit=8,
        )

        sql, params = cursor.execute.call_args[0]
        # Conversations are now shared - filter by conversation_key only
        assert "c.conversation_key = %s" in sql
        assert "m.agent_name = %s" not in sql  # No longer filtering by agent_name
        assert "c.agent_name = %s" not in sql  # No longer filtering by agent_name
        assert params[0] == "slack:C123:171234.1000:U111"
        assert rows[0]["role"] == "user"
        assert rows[1]["role"] == "assistant"


def test_upsert_memory_is_agent_scoped():
    with patch("src.db.context_store.psycopg2.connect") as mock_connect:
        conn = MagicMock()
        mock_connect.return_value = conn

        cursor = conn.cursor.return_value
        store = AgentContextStore()
        success = store.upsert_memory(
            agent_name="Vito",
            memory_key="risk_tolerance",
            memory_value="conservative",
            metadata={"source": "manual"},
        )

        assert success is True
        sql, params = cursor.execute.call_args[0]
        assert "agent_memories" in sql
        assert params[0] == "Vito"
        assert params[1] == "risk_tolerance"
        assert params[2] == "conservative"
