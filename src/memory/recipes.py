"""
Per-agent memory retrieval configuration.

Each agent gets a MemoryRecipe that declares what memory sources to query
and how to blend them. This is a declarative configuration table — the
same pattern as ROUTING_TABLE in src/llm/models.py — keeping memory
policy centralized and tunable without touching agent code.

Design decisions
----------------
Why a config table (not per-agent methods):
    Memory retrieval logic is the same across agents — embed query, search
    Weaviate, query MongoDB, merge results. What differs is the parameters:
    which collections, how many results, what alpha. A config table captures
    these differences as data, not code.

    If an agent needs truly custom retrieval (e.g., multi-hop reasoning),
    it can override the retrieve_memories() function. But for the standard
    blend-and-rank pattern, the recipe table is sufficient.

Why frozen dataclass:
    Recipes are immutable configuration. Using frozen=True prevents
    accidental mutation and makes them safe to share across threads
    (relevant for the thread pool used by embedding generation).

Weight semantics:
    - relevance_weight: proportion of results from Weaviate (semantic search).
    - recency_weight: proportion of results from MongoDB (sorted by created_at).
    - The weights do not need to sum to 1.0 — they control whether each
      source is queried at all (weight > 0) and how many results to take
      from each source relative to max_results.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryRecipe:
    """
    Retrieval configuration for a single agent.

    Attributes:
        relevance_weight: 0.0-1.0, proportion of results from Weaviate
            semantic search. 0.0 = skip Weaviate entirely.
        recency_weight: 0.0-1.0, proportion of results from MongoDB
            recency queries. 0.0 = skip MongoDB entirely.
        weaviate_collections: Which Weaviate collections to search.
        mongodb_collections: Which MongoDB collections to query for
            recent items (by created_at descending).
        max_results: Total number of memory items to return after merging.
        hybrid_alpha: Weaviate hybrid search alpha — 1.0 = pure vector,
            0.0 = pure BM25, 0.7 = default blend.
    """

    relevance_weight: float
    recency_weight: float
    weaviate_collections: tuple[str, ...]
    mongodb_collections: tuple[str, ...]
    max_results: int = 5
    hybrid_alpha: float = 0.7


# ---------------------------------------------------------------------------
# Recipe table: agent_name -> MemoryRecipe
# ---------------------------------------------------------------------------
# Recipes for agents defined so far. New agents added in future modules
# should register their recipes here.

MEMORY_RECIPES: dict[str, MemoryRecipe] = {
    # RequirementsAnalyst extracts job requirements — benefits from seeing
    # the user's resume context and past job descriptions for comparison.
    "requirements_analyst": MemoryRecipe(
        relevance_weight=0.8,
        recency_weight=0.2,
        weaviate_collections=("ResumeChunk", "JobEmbedding"),
        mongodb_collections=("jobs",),
        max_results=5,
        hybrid_alpha=0.7,
    ),
    # CoverLetterWriter needs resume sections matching the JD plus examples
    # of past cover letters for similar roles.
    "cover_letter_writer": MemoryRecipe(
        relevance_weight=0.7,
        recency_weight=0.3,
        weaviate_collections=("ResumeChunk", "CoverLetterEmbedding"),
        mongodb_collections=("documents",),
        max_results=5,
        hybrid_alpha=0.7,
    ),
}
