"""
Memory retrieval orchestrator — the central entry point for agents.

Given an agent name and a query, retrieves relevant context from both
Weaviate (semantic similarity) and MongoDB (temporal recency), merges
the results according to the agent's MemoryRecipe, and returns a
formatted MemoryContext ready for prompt injection.

Design decisions
----------------
Why a single entry point (not per-agent retrieval functions):
    All agents follow the same retrieval pattern: search Weaviate for
    semantically relevant items, query MongoDB for recent items, blend
    by weights, format for prompt. The only differences are the parameters
    (which collections, how many results, what alpha), captured in the
    MEMORY_RECIPES config table.

    A single retrieve_memories() function keeps the retrieval logic in
    one place. Agents just call retrieve_memories("cover_letter_writer",
    query, user_id) and get back formatted context.

Why separate Weaviate and MongoDB retrieval steps:
    Weaviate and MongoDB serve different retrieval needs:
    - Weaviate: "find semantically similar" — resume chunks matching a JD,
      past cover letters for similar roles.
    - MongoDB: "find recent" — the last few cover letters written, recent
      job applications. Recency matters for context (what has the user
      been working on?).

    Keeping them separate allows the recipe to control the blend and to
    skip one source entirely (e.g., requirements_analyst uses 80% Weaviate
    and 20% MongoDB — if we set recency_weight=0.0, MongoDB is never queried).

Usage
-----
    from src.memory.retrieval import retrieve_memories

    context = await retrieve_memories("cover_letter_writer", "Python backend role", "user-123")
    # context.formatted -> "## Relevant Context\n\n### Resume Sections\n..."
    # context.items -> [MemoryItem(...), MemoryItem(...), ...]
"""

import structlog

from src.memory.recipes import MEMORY_RECIPES
from src.memory.types import MemoryContext, MemoryItem
from src.rag.retriever import hybrid_search

logger = structlog.get_logger()


async def retrieve_memories(
    agent_name: str,
    query: str,
    user_id: str,
) -> MemoryContext:
    """
    Retrieve memory context for an agent based on its recipe.

    Steps:
    1. Look up the agent's MemoryRecipe.
    2. If relevance_weight > 0: search each configured Weaviate collection.
    3. Score Weaviate results by relevance_weight * search_score.
    4. Merge, sort by score, take top max_results.
    5. Format into a MemoryContext with human-readable text.

    MongoDB recency queries (step between 2 and 4 in the full plan) are
    stubbed for now — they require the collection-specific MongoDB
    repositories that will be integrated when those modules are built.
    The retrieval pipeline is designed to add them without changing the
    interface.

    Args:
        agent_name: The agent requesting memory (must be in MEMORY_RECIPES).
        query: The query text to search for (e.g., job description, question).
        user_id: The user's ID (used as Weaviate tenant and MongoDB filter).

    Returns:
        MemoryContext with retrieved items and formatted text.

    Raises:
        ValueError: If agent_name is not in MEMORY_RECIPES.
    """
    recipe = MEMORY_RECIPES.get(agent_name)
    if recipe is None:
        msg = (
            f"No memory recipe for agent '{agent_name}'. "
            f"Known agents: {sorted(MEMORY_RECIPES.keys())}"
        )
        raise ValueError(msg)

    items: list[MemoryItem] = []

    # -- Weaviate semantic search --
    if recipe.relevance_weight > 0:
        for collection in recipe.weaviate_collections:
            try:
                results = await hybrid_search(
                    collection_name=collection,
                    query=query,
                    tenant=user_id,
                    limit=recipe.max_results,
                    alpha=recipe.hybrid_alpha,
                )
                for result in results:
                    # Extract the primary text content from properties.
                    # Different collections use different field names for
                    # their main text content.
                    content = _extract_content(result["properties"], collection)
                    items.append(
                        MemoryItem(
                            content=content,
                            source="weaviate",
                            score=result.get("score", 0.0) * recipe.relevance_weight,
                            metadata={
                                "collection": collection,
                                "uuid": result["uuid"],
                                **result["properties"],
                            },
                        )
                    )
            except Exception:
                # Log but do not fail the entire retrieval if one collection
                # is unavailable (e.g., no tenant exists yet for a new user).
                logger.warning(
                    "memory_retrieval_failed",
                    collection=collection,
                    agent=agent_name,
                    user_id=user_id,
                    exc_info=True,
                )

    # Sort by score descending and take top results.
    items.sort(key=lambda item: item.score, reverse=True)
    items = items[: recipe.max_results]

    formatted = format_memory_context(items)

    logger.debug(
        "memory_retrieved",
        agent=agent_name,
        item_count=len(items),
        sources=[item.source for item in items],
    )

    return MemoryContext(items=items, formatted=formatted)


def _extract_content(properties: dict, collection: str) -> str:
    """
    Extract the primary text content field from a Weaviate result.

    Each collection stores its main text in a different property name.
    This function maps collection names to their content fields.
    """
    content_fields: dict[str, str] = {
        "ResumeChunk": "content",
        "JobEmbedding": "description_summary",
        "CoverLetterEmbedding": "content_summary",
        "STARStoryEmbedding": "story_summary",
    }
    field_name = content_fields.get(collection, "content")
    return properties.get(field_name, "")


def format_memory_context(items: list[MemoryItem]) -> str:
    """
    Format memory items into a text block for prompt injection.

    Groups items by their source collection and formats them with headers
    and numbered entries. This pre-formatted text is included in the agent's
    prompt so it does not need to parse structured data.

    Returns an empty string if no items are provided — agents check for
    empty memory_context before including it in their prompts.
    """
    if not items:
        return ""

    # Group items by collection for readable formatting.
    groups: dict[str, list[MemoryItem]] = {}
    for item in items:
        collection = item.metadata.get("collection", item.source)
        groups.setdefault(collection, []).append(item)

    sections: list[str] = ["## Relevant Context from Memory"]
    for collection, group_items in groups.items():
        # Readable collection name: "ResumeChunk" -> "Resume Chunk"
        display_name = _humanize_collection_name(collection)
        sections.append(f"\n### {display_name}")
        for i, item in enumerate(group_items, 1):
            sections.append(f"{i}. {item.content}")

    return "\n".join(sections)


def _humanize_collection_name(name: str) -> str:
    """Convert a PascalCase collection name to a readable display name."""
    # Insert spaces before uppercase letters: "ResumeChunk" -> "Resume Chunk"
    result: list[str] = []
    for char in name:
        if char.isupper() and result:
            result.append(" ")
        result.append(char)
    return "".join(result)
