import pytest
import json
import os
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

# Use module-based imports to ensure patching is reliable
import famiglia_core.db.tools.user_connections_store as store_mod

# A stable key for all tests
_TEST_KEY = Fernet.generate_key()
_TEST_KEY_STR = _TEST_KEY.decode()

class TestGetFernet:
    def test_uses_env_var_when_set(self):
        with patch.dict("os.environ", {"FERNET_SECRET": _TEST_KEY_STR}):
            f = store_mod._get_fernet()
        token = f.encrypt(b"hello")
        assert f.decrypt(token) == b"hello"

    def test_reads_existing_key_file(self, tmp_path):
        key_file = tmp_path / "fernet.key"
        key_file.write_text(_TEST_KEY_STR)

        with patch.object(store_mod, "_FERNET_KEY_FILE", str(key_file)):
            with patch.dict("os.environ", {}, clear=True):
                # Ensure no cached secret
                os.environ.pop("FERNET_SECRET", None)
                f = store_mod._get_fernet()

        token = f.encrypt(b"data")
        assert f.decrypt(token) == b"data"

    def test_generates_and_persists_key_when_file_missing(self, tmp_path):
        key_file = tmp_path / "fernet.key"
        # We must also mock the SECRETS_DIR if we want to be truly safe, 
        # but patching _FERNET_KEY_FILE directly is usually enough if _get_fernet uses it.
        with patch.object(store_mod, "_FERNET_KEY_FILE", str(key_file)):
            with patch.dict("os.environ", {}, clear=True):
                os.environ.pop("FERNET_SECRET", None)
                f = store_mod._get_fernet()

        assert key_file.exists()
        persisted = key_file.read_text().strip()
        from cryptography.fernet import Fernet as F
        assert F(persisted.encode()).decrypt(f.encrypt(b"x")) == b"x"


@pytest.fixture
def stable_fernet():
    fernet_instance = Fernet(_TEST_KEY)
    # Patch the function called by the Store
    with patch.object(store_mod, "_get_fernet", return_value=fernet_instance):
        yield fernet_instance

@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    # Ensure fetchone defaults to None so it doesn't return a truthy Mock
    cursor.fetchone.return_value = None
    return cursor

@pytest.fixture
def mock_db_session(mock_cursor):
    cm = MagicMock()
    cm.__enter__.return_value = mock_cursor
    cm.__exit__.return_value = False
    # Patch the singleton's method
    with patch.object(store_mod.context_store, "db_session", return_value=cm):
        yield cm, mock_cursor

@pytest.fixture
def store(stable_fernet):
    """Return a fresh instance of the store."""
    return store_mod.UserConnectionsStore()

class TestUpsertConnection:
    def test_encrypts_token_before_storing(self, store, mock_db_session, stable_fernet):
        _, cursor = mock_db_session
        result = store.upsert_connection(service="ollama", access_token="plain-key")
        assert result is True
        assert cursor.execute.called
        call_args = cursor.execute.call_args[0][1]
        stored_token = call_args[3]
        assert stored_token != "plain-key"
        assert stable_fernet.decrypt(stored_token.encode()).decode() == "plain-key"

    def test_on_conflict_targets_service(self, store, mock_db_session):
        _, cursor = mock_db_session
        store.upsert_connection(service="slack", access_token="token")
        assert cursor.execute.called
        sql = cursor.execute.call_args[0][0].upper()
        assert "ON CONFLICT (SERVICE)" in sql

    def test_stores_metadata_as_scopes(self, store, mock_db_session):
        _, cursor = mock_db_session
        meta = {"a": 1}
        store.upsert_connection(service="s", access_token="t", scopes=json.dumps(meta))
        assert cursor.execute.called
        call_args = cursor.execute.call_args[0][1]
        assert json.loads(call_args[4]) == meta

class TestGetConnection:
    def test_decrypts_token_on_retrieval(self, store, mock_db_session, stable_fernet):
        _, cursor = mock_db_session
        enc = stable_fernet.encrypt(b"secret").decode()
        cursor.fetchone.return_value = {
            "service": "s", "username": "u", "avatar_url": None, "access_token": enc,
            "scopes": None, "app_id": None, "refresh_token": None, "connected_at": None, "updated_at": None
        }
        res = store.get_connection("s")
        assert res is not None
        assert res["access_token"] == "secret"

    def test_returns_none_when_no_row(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = None
        assert store.get_connection("s") is None

class TestGetConnectionStatus:
    def test_returns_connected_true(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = {
            "username": "u", "avatar_url": None, "scopes": None, "app_id": "aid", "refresh_token": "rt", "connected_at": None
        }
        res = store.get_connection_status("s")
        assert res["connected"] is True
        assert res["rotatable"] is True

    def test_returns_false_when_no_row(self, store, mock_db_session):
        _, cursor = mock_db_session
        cursor.fetchone.return_value = None
        assert store.get_connection_status("s") == {"connected": False}

class TestDeleteConnection:
    def test_deletes_returns_true(self, store, mock_db_session):
        _, cursor = mock_db_session
        assert store.delete_connection("s") is True
        assert cursor.execute.called
        assert "DELETE FROM user_connections" in cursor.execute.call_args[0][0]
