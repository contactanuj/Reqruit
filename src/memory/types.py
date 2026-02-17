"""
Data structures for the memory system.

These types flow through the memory pipeline: retrieval functions produce
MemoryItems, which are collected into a MemoryContext, which is injected
into agent state for prompt construction.

Using dataclasses (not Pydantic models) because these are internal data
transfer objects — they do not cross the API boundary, do not need JSON
schema generation, and do not need validation beyond what the retrieval
functions guarantee. Dataclasses are lighter weight and sufficient here.
"""

from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    """
    A single piece of retrieved context from the memory system.

    Represents one search result — either a Weaviate vector search hit
    or a MongoDB recency query result. The score is normalized to 0.0-1.0
    regardless of source, allowing items from different sources to be
    ranked together.

    Attributes:
        content: The actual text content (resume chunk, past cover letter, etc.).
        source: Where the item came from — "weaviate" or "mongodb".
        score: Relevance or recency score, normalized to 0.0-1.0.
        metadata: Collection-specific fields (company, role, chunk_type, etc.).
    """

    content: str
    source: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryContext:
    """
    Aggregated memory context ready for prompt injection.

    Contains the raw items (for inspection/debugging) and a pre-formatted
    text block that agents include directly in their prompts. The formatted
    text is built by format_memory_context() and avoids each agent needing
    to format memory items differently.

    Attributes:
        items: The individual memory items, sorted by score descending.
        formatted: Human-readable text block for prompt injection.
    """

    items: list[MemoryItem] = field(default_factory=list)
    formatted: str = ""
