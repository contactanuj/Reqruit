"""
Embedding service lifecycle for BGE-small-en-v1.5.

Provides module-level init/close/get functions matching the pattern
established by mongodb.py, weaviate_client.py, manager.py, and
checkpointer.py. The FastAPI lifespan calls init on startup and close
on shutdown; all other code accesses the service via get_embedding_service().

Design decisions
----------------
Why BGE-small-en-v1.5 (not OpenAI ada-002 or Cohere embed):
    Free, local, offline. No API costs per embedding, no rate limits, no
    vendor lock-in. The 384-dimension vectors are compact enough for fast
    similarity search while retaining good quality for our retrieval tasks.

    Tradeoff: slightly lower quality than ada-002 on general benchmarks,
    but BGE-small ranks well on the MTEB leaderboard for retrieval tasks
    and runs entirely on-device. For a learning project with frequent
    re-indexing during development, zero API cost wins.

Why app-side embeddings (not Weaviate vectorizer modules):
    Weaviate's text2vec-openai would add API costs per embedding and
    require internet access. By generating embeddings in our application,
    we keep full control over the model, can embed before storing (useful
    for validation), and can reuse the same model for both indexing and
    query-time embedding.

Why asyncio.to_thread for embed calls:
    HuggingFaceEmbeddings.embed_documents() and embed_query() are
    synchronous and CPU-bound (matrix multiplication in PyTorch). Running
    them directly in an async context would block the event loop and stall
    all concurrent requests.

    asyncio.to_thread() offloads the call to a thread pool worker, keeping
    the event loop responsive. The GIL is partially released during the
    underlying C/CUDA operations, so there is real concurrency benefit.

Why normalize_embeddings=True:
    BGE models are trained with cosine similarity. Normalizing embeddings
    to unit length at generation time means cosine similarity = dot product,
    which is faster to compute. Weaviate's HNSW cosine index benefits from
    this since normalized vectors avoid the extra normalization step during
    each distance calculation.

Usage
-----
In the FastAPI lifespan (src/api/main.py):
    from src.rag.embeddings import init_embeddings, close_embeddings

    async def lifespan(app):
        await connect_mongodb(settings)
        await connect_weaviate(settings)
        init_embeddings(settings)       # Loads the model (~2-3 seconds)
        yield
        close_embeddings()

In a repository or service:
    from src.rag.embeddings import embed_texts, embed_query

    vectors = await embed_texts(["chunk 1", "chunk 2"])   # list[list[float]]
    query_vec = await embed_query("Python FastAPI developer")  # list[float]
"""

import asyncio

import structlog
from langchain_huggingface import HuggingFaceEmbeddings

from src.core.config import Settings
from src.core.exceptions import EmbeddingError

logger = structlog.get_logger()

# Module-level embedding model reference. Set by init_embeddings(),
# cleared by close_embeddings().
_embeddings: HuggingFaceEmbeddings | None = None


# ---------------------------------------------------------------------------
# Lifecycle functions
# ---------------------------------------------------------------------------


def init_embeddings(settings: Settings) -> None:
    """
    Load the embedding model into memory.

    Creates a HuggingFaceEmbeddings instance with the model specified in
    settings. The model weights (~130MB for BGE-small) are downloaded on
    first run and cached by HuggingFace's hub library.

    This is a synchronous operation (model loading is CPU-bound) and takes
    2-3 seconds. Called once during FastAPI startup.

    Args:
        settings: Application settings containing embedding model config.
    """
    global _embeddings

    model_kwargs: dict = {"device": "cpu"}
    encode_kwargs: dict = {"normalize_embeddings": True}

    # Use a custom cache directory if configured, otherwise HuggingFace
    # defaults to ~/.cache/huggingface/hub.
    if settings.embedding.cache_dir:
        model_kwargs["cache_folder"] = settings.embedding.cache_dir

    logger.info(
        "embeddings_loading",
        model=settings.embedding.model_name,
        dimensions=settings.embedding.dimensions,
    )

    _embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding.model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs,
    )

    logger.info("embeddings_loaded", model=settings.embedding.model_name)


def close_embeddings() -> None:
    """
    Release the embedding model.

    Clears the module-level reference so the model can be garbage collected.
    Safe to call multiple times (idempotent).
    """
    global _embeddings

    if _embeddings is not None:
        _embeddings = None
        logger.info("embeddings_closed")


def get_embedding_service() -> HuggingFaceEmbeddings:
    """
    Return the active embedding model instance.

    For use in repositories and services that need to generate embeddings
    before storing or searching in Weaviate.

    Raises:
        RuntimeError: If called before init_embeddings().
    """
    if _embeddings is None:
        msg = "Embedding service not initialized. Call init_embeddings() first."
        raise RuntimeError(msg)
    return _embeddings


# ---------------------------------------------------------------------------
# Async embedding wrappers
# ---------------------------------------------------------------------------
# HuggingFaceEmbeddings methods are synchronous and CPU-bound. These async
# wrappers offload the work to a thread pool so the event loop stays free.


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.

    Used when indexing documents (resumes, cover letters, STAR stories) into
    Weaviate. Each text is embedded independently; the model handles batching
    internally for efficiency.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors, one per input text. Each vector has
        384 dimensions (for BGE-small-en-v1.5).

    Raises:
        EmbeddingError: If the embedding model fails or is not initialized.
    """
    service = get_embedding_service()

    try:
        return await asyncio.to_thread(service.embed_documents, texts)
    except RuntimeError:
        # Re-raise RuntimeError from get_embedding_service() as-is
        raise
    except Exception as exc:
        raise EmbeddingError(
            detail=f"Failed to embed {len(texts)} text(s): {exc}"
        ) from exc


async def embed_query(text: str) -> list[float]:
    """
    Generate an embedding for a single query text.

    Used at search time when the user or agent provides a query. BGE models
    prepend a query instruction ("Represent this sentence for searching
    relevant passages:") to improve retrieval quality — this happens
    automatically inside HuggingFaceEmbeddings.embed_query().

    The distinction between embed_documents and embed_query matters for BGE:
    documents are embedded as-is, queries get the instruction prefix. Using
    embed_query for search queries and embed_texts for indexing ensures the
    best retrieval accuracy.

    Args:
        text: The query text to embed.

    Returns:
        A single embedding vector (384 dimensions for BGE-small-en-v1.5).

    Raises:
        EmbeddingError: If the embedding model fails or is not initialized.
    """
    service = get_embedding_service()

    try:
        return await asyncio.to_thread(service.embed_query, text)
    except RuntimeError:
        raise
    except Exception as exc:
        raise EmbeddingError(
            detail=f"Failed to embed query: {exc}"
        ) from exc
