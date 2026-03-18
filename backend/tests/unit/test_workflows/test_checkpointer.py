"""
Tests for the checkpointer lifecycle — init, get, close.

MongoClient and MongoDBSaver are mocked to avoid needing a real MongoDB
instance. These tests verify the module-level lifecycle pattern works
correctly: init creates the instances, get returns them, close cleans up,
and the whole cycle is repeatable.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.workflows.checkpointer import (
    close_checkpointer,
    get_checkpointer,
    init_checkpointer,
)


@pytest.fixture(autouse=True)
def _reset_checkpointer():
    """Ensure each test starts with a clean module state."""
    # Reset before test
    import src.workflows.checkpointer as mod

    mod._sync_client = None
    mod._checkpointer = None
    yield
    # Reset after test
    mod._sync_client = None
    mod._checkpointer = None


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.mongodb.url = "mongodb://localhost:27017"
    settings.mongodb.database = "test_db"
    return settings


class TestCheckpointerLifecycle:
    def test_get_raises_before_init(self):
        with pytest.raises(RuntimeError, match="Checkpointer not initialized"):
            get_checkpointer()

    @patch("src.workflows.checkpointer.MongoDBSaver")
    @patch("src.workflows.checkpointer.MongoClient")
    def test_init_creates_checkpointer(
        self, mock_client_cls, mock_saver_cls, mock_settings
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_saver = MagicMock()
        mock_saver_cls.return_value = mock_saver

        init_checkpointer(mock_settings)

        mock_client_cls.assert_called_once_with("mongodb://localhost:27017")
        mock_saver_cls.assert_called_once_with(
            client=mock_client, db_name="test_db"
        )
        assert get_checkpointer() is mock_saver

    @patch("src.workflows.checkpointer.MongoDBSaver")
    @patch("src.workflows.checkpointer.MongoClient")
    def test_close_clears_and_closes_client(
        self, mock_client_cls, mock_saver_cls, mock_settings
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        init_checkpointer(mock_settings)
        close_checkpointer()

        mock_client.close.assert_called_once()
        with pytest.raises(RuntimeError):
            get_checkpointer()

    def test_close_is_idempotent(self):
        """Calling close when not initialized should not raise."""
        close_checkpointer()  # Should not raise
        close_checkpointer()  # Should not raise again

    @patch("src.workflows.checkpointer.MongoDBSaver")
    @patch("src.workflows.checkpointer.MongoClient")
    def test_init_close_init_cycle(
        self, mock_client_cls, mock_saver_cls, mock_settings
    ):
        """Verify the checkpointer can be re-initialized after closing."""
        init_checkpointer(mock_settings)
        close_checkpointer()
        init_checkpointer(mock_settings)

        # Second init should work and return a usable checkpointer
        assert get_checkpointer() is not None
