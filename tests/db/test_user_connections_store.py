"""
Tests for UserConnectionsStore — Fernet encryption, upsert, get, delete.
All DB calls and Fernet key loading are mocked to keep tests hermetic.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

from famiglia_core.db.tools.user_connections_store import UserConnectionsStore, _get_fernet

# A stable key for all tests so encryption/decryption is deterministic.
_TEST_KEY = Fernet.generate_key()
_TEST_KEY_STR = _TEST_KEY.decode()


# ─── _get_fernet ──────────────────────────────────────────────────────────────

class TestGetFernet:
    def test_uses_env_var_when_set(self):
        with patch.dict("os.environ", {"FERNET_SECRET": _TEST_KEY_STR}):
            f = _get_fernet()
        # Should be able to encrypt/decrypt a round-trip
        token = f.encrypt(b"hello")
        assert f.decrypt(token) == b"hello"

    def test_reads_existing_key_file(self, tmp_path):
        key_file = tmp_path / "fernet.key"
        key_file.write_text(_TEST_KEY_STR)

        with patch("famiglia_core.db.tools.user_connections_store._FERNET_KEY_FILE", str(key_file)):
            with patch.dict("os.environ", {}, clear=True):
                # Remove FERNET_SECRET if present
                import os
                os.environ.pop("FERNET_SECRET", None)
                f = _get_fernet()

        token = f.encrypt(b"data")
        assert f.decrypt(token) == b"data"

    def test_generates_and_persists_key_when_file_missing(self, tmp_path):
        key_file = tmp_path / "fernet.key"

        with patch("famiglia_core.db.tools.user_connections_store._FERNET_KEY_FILE", str(key_file)):
            import os
            os.environ.pop("FERNET_SECRET", None)
            f = _get_fernet()

        assert key_file.exists()
        persisted = key_file.read_text().strip()
        # Persisted key should decrypt what was just encrypted
        from cryptography.fernet import Fernet as F
        assert F(persisted.encode()).decrypt(f.encrypt(b"x")) == b"x"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def store():
    return UserConnectionsStore()


@pytest.fixture(autouse=True)
def stable_fernet():
    """Pin Fernet to a stable test key so encryption is deterministic."""
    fernet_instance = Fernet(_TEST_KEY)
    with patch("famiglia_core.db.tools.user_connections_store._get_fernet", return_value=fernet_instance):
        yield fernet_instance


@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    return cursor


@pytest.fixture
def mock_db_session(mock_cursor):
    """Patch context_store.db_session to yield mock_cursor."""
    cm = MagicMock()
    cm.__enter__.return_value = mock_cursor
    cm.__exit__.return_value = False
    with patch(
        "famiglia_core.db.tools.user_connections_store.context_store.db_session",
        return_value=cm,
    ) as patched:
        yield patched, mock_cursor


# ─── upsert_connection ────────────────────────────────────────────────────────

class TestUpsertConnection:
    def test_encrypts_token_before_storing(self, store, mock_db_session, stable_fernet):
        _, cursor = mock_db_session
        result = store.upsert_connection(
            service="ollama",
            access_token="plain-api-key",
            username="don_jimmy",
        )
        assert result is True
        call_args = cursor.execute.call_args[0][1]
        stored_token = call_args[3]
        # Token in DB must be ciphertext, not plaintext
        assert stored_token != "plain-api-key"
        # But must decrypt back to plaintext
        assert stable_fernet.decrypt(stored_token.encode()).decode() == "plain-api-key"

    def test_returns_false_when_cursor_is_none(self, store):
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            result = store.upsert_connection(service="ollama", access_token="key")
        assert result is False

    def test_returns_false_on_db_exception(self, store):
        cm = MagicMock()
        cm.__enter__.side_effect = Exception("DB error")
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            result = store.upsert_connection(service="ollama", access_token="key")
        assert result is False

    def test_on_conflict_targets_service(self, store, mock_db_session):
        _, cursor = mock_db_session
        store.upsert_connection(service="slack_bot:alfredo", access_token="token")
        sql = cursor.execute.call_args[0][0].upper()
        # Verify the ON CONFLICT clause targets only the service column now
        assert "ON CONFLICT (SERVICE)" in sql
        assert "USER_ID" not in sql.split("ON CONFLICT")[1]

    def test_stores_metadata_as_scopes(self, store, mock_db_session):
        _, cursor = mock_db_session
        metadata = {"transport": "http", "public_url": "https://ngrok.io"}
        store.upsert_connection(
            service="slack_creds:alfredo", 
            access_token="{}", 
            scopes=json.dumps(metadata)
        )
        call_args = cursor.execute.call_args[0][1]
        stored_metadata = call_args[4] # scopes is the 5th param
        assert json.loads(stored_metadata)["transport"] == "http"


# ─── get_connection ───────────────────────────────────────────────────────────

class TestGetConnection:
    def test_decrypts_token_on_retrieval(self, store, mock_db_session, stable_fernet):
        _, cursor = mock_db_session
        encrypted = stable_fernet.encrypt(b"plain-api-key").decode()
        cursor.fetchone.return_value = {
            "service": "ollama",
            "username": None,
            "avatar_url": None,
            "access_token": encrypted,
            "scopes": None,
            "connected_at": None,
            "updated_at": None,
        }
        result = store.get_connection("ollama")
        assert result is not None
        assert result["access_token"] == "plain-api-key"
        assert result["service"] == "ollama"

    def test_returns_none_when_no_row(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = None
        result = store.get_connection("ollama")
        assert result is None

    def test_returns_none_when_decryption_fails(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = {
            "service": "ollama",
            "username": None,
            "avatar_url": None,
            "access_token": "not-valid-ciphertext",
            "scopes": None,
            "connected_at": None,
            "updated_at": None,
        }
        result = store.get_connection("ollama")
        assert result is None

    def test_returns_none_when_cursor_is_none(self, store):
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            result = store.get_connection("ollama")
        assert result is None


# ─── get_connection_status ────────────────────────────────────────────────────

class TestGetConnectionStatus:
    def test_returns_connected_true_with_metadata(self, store, mock_db_session):
        from datetime import datetime, timezone
        _, cursor = mock_db_session
        ts = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
        cursor.fetchone.return_value = {
            "username": "don_jimmy",
            "avatar_url": None,
            "scopes": None,
            "connected_at": ts,
        }
        status = store.get_connection_status("ollama")
        assert status["connected"] is True
        assert status["username"] == "don_jimmy"
        assert "2026-04-15" in status["connected_at"]

    def test_returns_connected_false_when_no_row(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = None
        status = store.get_connection_status("ollama")
        assert status == {"connected": False}

    def test_returns_connected_false_when_cursor_is_none(self, store):
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            status = store.get_connection_status("ollama")
        assert status == {"connected": False}


# ─── delete_connection ────────────────────────────────────────────────────────

class TestDeleteConnection:
    def test_deletes_and_returns_true(self, store, mock_db_session):
        _, cursor = mock_db_session
        result = store.delete_connection("ollama")
        assert result is True
        sql = cursor.execute.call_args[0][0]
        assert "DELETE FROM user_connections" in sql

    def test_returns_false_when_cursor_is_none(self, store):
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            result = store.delete_connection("ollama")
        assert result is False

    def test_returns_false_on_db_exception(self, store):
        cm = MagicMock()
        cm.__enter__.side_effect = Exception("DB error")
        cm.__exit__.return_value = False
        with patch("famiglia_core.db.tools.user_connections_store.context_store.db_session", return_value=cm):
            result = store.delete_connection("ollama")
        assert result is False
