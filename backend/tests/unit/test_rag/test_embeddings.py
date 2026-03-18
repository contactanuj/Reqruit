"""
Tests for the embedding service lifecycle and async wrappers.

Verifies the init/close/get lifecycle pattern, the asyncio.to_thread
wrappers for embed_texts and embed_query, and error handling. The actual
HuggingFaceEmbeddings model is mocked — these tests focus on the
lifecycle management and async plumbing, not the model's output quality.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import EmbeddingSettings, Settings
from src.core.exceptions import EmbeddingError
from src.rag import embeddings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_embeddings():
    """Ensure the module-level state is clean before and after each test."""
    embeddings._embeddings = None
    yield
    embeddings._embeddings = None


@pytest.fixture
def mock_hf_embeddings():
    """Create a mock HuggingFaceEmbeddings instance."""
    mock = MagicMock()
    mock.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]
    mock.embed_query.return_value = [0.3] * 384
    return mock


@pytest.fixture
def test_settings() -> Settings:
    """Settings with default embedding config."""
    settings = MagicMock(spec=Settings)
    settings.embedding = EmbeddingSettings()
    return settings


# ---------------------------------------------------------------------------
# Lifecycle: init / close / get
# ---------------------------------------------------------------------------


class TestEmbeddingLifecycle:
    def test_get_raises_before_init(self):
        """get_embedding_service() raises RuntimeError when not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            embeddings.get_embedding_service()

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_init_creates_instance(self, mock_hf_cls, test_settings):
        """init_embeddings() creates the HuggingFaceEmbeddings instance."""
        embeddings.init_embeddings(test_settings)

        mock_hf_cls.assert_called_once()
        assert embeddings._embeddings is not None

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_init_passes_model_name(self, mock_hf_cls, test_settings):
        """init_embeddings() uses the model name from settings."""
        embeddings.init_embeddings(test_settings)

        call_kwargs = mock_hf_cls.call_args[1]
        assert call_kwargs["model_name"] == "BAAI/bge-small-en-v1.5"

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_init_sets_normalize_embeddings(self, mock_hf_cls, test_settings):
        """init_embeddings() enables embedding normalization."""
        embeddings.init_embeddings(test_settings)

        call_kwargs = mock_hf_cls.call_args[1]
        assert call_kwargs["encode_kwargs"]["normalize_embeddings"] is True

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_init_sets_cpu_device(self, mock_hf_cls, test_settings):
        """init_embeddings() sets device to cpu."""
        embeddings.init_embeddings(test_settings)

        call_kwargs = mock_hf_cls.call_args[1]
        assert call_kwargs["model_kwargs"]["device"] == "cpu"

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_init_with_custom_cache_dir(self, mock_hf_cls):
        """init_embeddings() passes cache_dir when configured."""
        settings = MagicMock(spec=Settings)
        settings.embedding = EmbeddingSettings(cache_dir="/tmp/models")

        embeddings.init_embeddings(settings)

        call_kwargs = mock_hf_cls.call_args[1]
        assert call_kwargs["model_kwargs"]["cache_folder"] == "/tmp/models"

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_get_returns_instance_after_init(self, mock_hf_cls, test_settings):
        """get_embedding_service() returns the model after initialization."""
        embeddings.init_embeddings(test_settings)
        result = embeddings.get_embedding_service()
        assert result is mock_hf_cls.return_value

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_close_clears_instance(self, mock_hf_cls, test_settings):
        """close_embeddings() clears the module-level reference."""
        embeddings.init_embeddings(test_settings)
        embeddings.close_embeddings()

        assert embeddings._embeddings is None

    def test_close_idempotent(self):
        """close_embeddings() does not raise when called without init."""
        embeddings.close_embeddings()
        embeddings.close_embeddings()
        # No exception = pass

    @patch("src.rag.embeddings.HuggingFaceEmbeddings")
    def test_get_raises_after_close(self, mock_hf_cls, test_settings):
        """get_embedding_service() raises after close."""
        embeddings.init_embeddings(test_settings)
        embeddings.close_embeddings()

        with pytest.raises(RuntimeError, match="not initialized"):
            embeddings.get_embedding_service()


# ---------------------------------------------------------------------------
# Async wrappers: embed_texts / embed_query
# ---------------------------------------------------------------------------


class TestEmbedTexts:
    async def test_returns_vectors(self, mock_hf_embeddings):
        """embed_texts() returns a list of vectors from embed_documents."""
        embeddings._embeddings = mock_hf_embeddings

        result = await embeddings.embed_texts(["hello", "world"])

        assert len(result) == 2
        assert len(result[0]) == 384
        mock_hf_embeddings.embed_documents.assert_called_once_with(
            ["hello", "world"]
        )

    async def test_raises_embedding_error_on_failure(self, mock_hf_embeddings):
        """embed_texts() wraps model failures in EmbeddingError."""
        mock_hf_embeddings.embed_documents.side_effect = ValueError("bad input")
        embeddings._embeddings = mock_hf_embeddings

        with pytest.raises(EmbeddingError, match="Failed to embed 2 text"):
            await embeddings.embed_texts(["a", "b"])

    async def test_raises_runtime_error_when_not_initialized(self):
        """embed_texts() raises RuntimeError when service not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await embeddings.embed_texts(["test"])


class TestEmbedQuery:
    async def test_returns_single_vector(self, mock_hf_embeddings):
        """embed_query() returns a single vector from embed_query."""
        embeddings._embeddings = mock_hf_embeddings

        result = await embeddings.embed_query("test query")

        assert len(result) == 384
        mock_hf_embeddings.embed_query.assert_called_once_with("test query")

    async def test_raises_embedding_error_on_failure(self, mock_hf_embeddings):
        """embed_query() wraps model failures in EmbeddingError."""
        mock_hf_embeddings.embed_query.side_effect = RuntimeError("model error")
        embeddings._embeddings = mock_hf_embeddings

        # RuntimeError from the model (not from get_embedding_service) is
        # re-raised as-is since it could be from get_embedding_service().
        # But here the model is set, so the except RuntimeError: raise path
        # triggers. We set a different exception type to test EmbeddingError.
        mock_hf_embeddings.embed_query.side_effect = ValueError("model error")

        with pytest.raises(EmbeddingError, match="Failed to embed query"):
            await embeddings.embed_query("test")

    async def test_raises_runtime_error_when_not_initialized(self):
        """embed_query() raises RuntimeError when service not initialized."""
        with pytest.raises(RuntimeError, match="not initialized"):
            await embeddings.embed_query("test")
