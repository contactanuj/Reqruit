"""
Document-aware chunking for the RAG indexing pipeline.

Splits resumes, job descriptions, and other text into semantically meaningful
chunks for embedding and storage in Weaviate. The chunking strategy depends
on document type:

- **Resumes**: Split by section headings (Work Experience, Education, Skills, etc.)
- **Job descriptions**: Split by section headings (Responsibilities, Requirements, etc.)
- **Other text**: Fixed-size chunks with token overlap

Design decisions
----------------
Why document-aware chunking (not just fixed-size everywhere):
    Resumes and job descriptions have a well-defined structure. A "Work
    Experience at Acme Corp" section is a coherent semantic unit — splitting
    it mid-paragraph would lose context and degrade embedding quality.

    Document-aware chunking keeps each section intact as a single chunk. The
    resulting embeddings are more meaningful for retrieval: when an agent asks
    "find resume sections about Python backend experience", a whole Work
    Experience chunk is more useful than a 500-token fragment.

Why regex-based section detection (not LLM-based):
    Section headings follow predictable patterns ("Education", "SKILLS:",
    "## Work Experience"). Regex is fast, deterministic, and free — no API
    calls needed. LLM-based splitting would be more accurate on messy
    documents but adds latency and cost for minimal benefit on our structured
    input formats.

Why fixed-size fallback with overlap:
    Some documents have no recognizable section headings (e.g., a free-form
    cover letter, a job description in paragraph form). Fixed-size chunking
    with overlap ensures every document can be indexed, even without
    structural cues. The 50-token overlap prevents context loss at chunk
    boundaries.

Why frozen Chunk dataclass:
    Chunks are intermediate data passed from the chunker to the embedding
    and storage stages. They should never be mutated after creation — a
    frozen dataclass enforces this at the language level, just like
    MemoryRecipe in src/memory/recipes.py.

Why word-count token estimation (not tiktoken):
    For chunking purposes, exact token counts are unnecessary. BGE-small
    uses a WordPiece tokenizer where most English words map to 1-2 tokens.
    Word count (whitespace split) is a fast, dependency-free approximation
    that is close enough for deciding chunk boundaries.

Usage
-----
    from src.rag.chunker import chunk_resume, chunk_job_description, chunk_fixed_size

    # Resume with section headings
    chunks = chunk_resume(raw_text="...", resume_id="abc", user_id="user-1")
    # [Chunk(content="5 years Python...", chunk_type="work_experience", metadata={...}), ...]

    # Job description
    chunks = chunk_job_description(description="...", job_id="xyz", user_id="user-1")

    # Arbitrary text
    chunks = chunk_fixed_size("Long text...", chunk_type="notes", metadata={"source": "manual"})
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Chunk dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """
    A single chunk of text ready for embedding.

    Produced by the chunking functions and consumed by the indexing service.
    Frozen to prevent mutation after creation — chunks are data that flows
    through the pipeline, not mutable state.

    Attributes:
        content: The chunk text content.
        chunk_type: Describes the section type (e.g., "work_experience",
            "skills", "fixed_size", "full_text").
        metadata: Source-specific fields carried through to Weaviate properties
            (e.g., resume_id, job_id, user_id).
    """

    content: str
    chunk_type: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Section heading patterns
# ---------------------------------------------------------------------------
# Compiled regex patterns for recognizing section headings in resumes and
# job descriptions. Each pattern matches common formatting variations:
# - Plain text: "Education"
# - With colon: "Education:"
# - Markdown heading: "## Education"
# - Uppercase: "EDUCATION"
# - Multi-word: "Work Experience"
#
# All patterns use IGNORECASE and MULTILINE so they match at the start of
# any line regardless of capitalization.

RESUME_SECTIONS: dict[str, re.Pattern] = {
    "summary": re.compile(
        r"^(?:#{1,3}\s*)?(?:professional\s+)?summary\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "objective": re.compile(
        r"^(?:#{1,3}\s*)?(?:career\s+)?objective\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "work_experience": re.compile(
        r"^(?:#{1,3}\s*)?(?:work\s+|professional\s+)?experience\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "education": re.compile(
        r"^(?:#{1,3}\s*)?education\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "skills": re.compile(
        r"^(?:#{1,3}\s*)?(?:technical\s+|core\s+)?skills\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "projects": re.compile(
        r"^(?:#{1,3}\s*)?(?:personal\s+|key\s+)?projects\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "certifications": re.compile(
        r"^(?:#{1,3}\s*)?certifications?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "awards": re.compile(
        r"^(?:#{1,3}\s*)?(?:awards?\s*(?:&|and)?\s*)?(?:honors?|achievements?|awards?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "publications": re.compile(
        r"^(?:#{1,3}\s*)?publications?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "volunteer": re.compile(
        r"^(?:#{1,3}\s*)?volunteer(?:\s+(?:experience|work))?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "languages": re.compile(
        r"^(?:#{1,3}\s*)?languages?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "references": re.compile(
        r"^(?:#{1,3}\s*)?references?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}

JD_SECTIONS: dict[str, re.Pattern] = {
    "about": re.compile(
        r"^(?:#{1,3}\s*)?about\s*(?:us|the\s+(?:company|team|role))?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "responsibilities": re.compile(
        r"^(?:#{1,3}\s*)?(?:key\s+)?responsibilities\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "requirements": re.compile(
        r"^(?:#{1,3}\s*)?(?:minimum\s+|basic\s+)?requirements?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "qualifications": re.compile(
        r"^(?:#{1,3}\s*)?(?:required\s+|preferred\s+|minimum\s+)?qualifications?\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "benefits": re.compile(
        r"^(?:#{1,3}\s*)?(?:benefits?\s*(?:&|and)?\s*)?(?:perks?|benefits?|compensation)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "how_to_apply": re.compile(
        r"^(?:#{1,3}\s*)?how\s+to\s+apply\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "about_the_team": re.compile(
        r"^(?:#{1,3}\s*)?about\s+the\s+team\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "what_youll_do": re.compile(
        r"^(?:#{1,3}\s*)?what\s+you(?:'ll|.ll|\s+will)\s+(?:do|build|work\s+on)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _split_by_sections(
    text: str, patterns: dict[str, re.Pattern]
) -> list[tuple[str, str]]:
    """
    Split text into sections based on heading patterns.

    Scans the text for all matching headings, records their positions, and
    splits the text into (section_name, section_content) tuples. Any content
    before the first recognized heading is captured as a "preamble" section.

    Args:
        text: The full document text to split.
        patterns: Dict mapping section names to compiled regex patterns.

    Returns:
        List of (section_name, section_content) tuples. May be empty if no
        headings are found. Content is stripped of leading/trailing whitespace.
    """
    # Find all heading matches with their positions
    matches: list[tuple[int, int, str]] = []  # (start, end, section_name)
    for section_name, pattern in patterns.items():
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), section_name))

    if not matches:
        return []

    # Sort by position in the document
    matches.sort(key=lambda m: m[0])

    sections: list[tuple[str, str]] = []

    # Capture content before the first heading as "preamble"
    first_start = matches[0][0]
    preamble = text[:first_start].strip()
    if preamble:
        sections.append(("preamble", preamble))

    # Extract content between consecutive headings
    for i, (_, end, section_name) in enumerate(matches):
        if i + 1 < len(matches):
            # Content runs until the next heading starts
            next_start = matches[i + 1][0]
            content = text[end:next_start].strip()
        else:
            # Last section runs to the end of the document
            content = text[end:].strip()

        if content:
            sections.append((section_name, content))

    return sections


# ---------------------------------------------------------------------------
# Public chunking functions
# ---------------------------------------------------------------------------


def chunk_resume(raw_text: str, resume_id: str, user_id: str) -> list[Chunk]:
    """
    Split a resume into semantically meaningful chunks by section.

    Attempts to split the resume by recognized section headings (Work
    Experience, Education, Skills, etc.). If no section headings are found,
    falls back to fixed-size chunking.

    Args:
        raw_text: The full resume text extracted from PDF/DOCX.
        resume_id: The MongoDB ObjectId of the Resume document (as string).
        user_id: The owner's user ID for multi-tenancy.

    Returns:
        List of Chunk objects, each representing a resume section or
        fixed-size fragment. Empty list if raw_text is empty.
    """
    if not raw_text or not raw_text.strip():
        return []

    metadata = {"resume_id": resume_id, "user_id": user_id}

    sections = _split_by_sections(raw_text, RESUME_SECTIONS)
    if not sections:
        # No recognized headings — fall back to fixed-size chunking
        return chunk_fixed_size(
            raw_text, chunk_type="full_text", metadata=metadata
        )

    return [
        Chunk(content=content, chunk_type=section_name, metadata=metadata)
        for section_name, content in sections
    ]


def chunk_job_description(
    description: str, job_id: str, user_id: str
) -> list[Chunk]:
    """
    Split a job description into semantically meaningful chunks by section.

    Attempts to split by recognized JD section headings (Responsibilities,
    Requirements, Qualifications, etc.). Falls back to fixed-size chunking
    if no headings are found.

    Args:
        description: The full job description text.
        job_id: The MongoDB ObjectId of the Job document (as string).
        user_id: The owner's user ID for multi-tenancy.

    Returns:
        List of Chunk objects. Empty list if description is empty.
    """
    if not description or not description.strip():
        return []

    metadata = {"job_id": job_id, "user_id": user_id}

    sections = _split_by_sections(description, JD_SECTIONS)
    if not sections:
        return chunk_fixed_size(
            description, chunk_type="full_text", metadata=metadata
        )

    return [
        Chunk(content=content, chunk_type=section_name, metadata=metadata)
        for section_name, content in sections
    ]


def chunk_fixed_size(
    text: str,
    chunk_type: str = "fixed_size",
    metadata: dict | None = None,
    max_tokens: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    Split text into fixed-size chunks with token overlap.

    Used as a fallback when document-aware splitting finds no section
    headings, or for arbitrary text that has no known structure.

    Token count is estimated by word count (whitespace split). This is an
    approximation — BGE-small's WordPiece tokenizer maps most English words
    to 1-2 tokens, so word count is a reasonable proxy for deciding chunk
    boundaries without pulling in a tokenizer dependency.

    Args:
        text: The text to split into chunks.
        chunk_type: Label for the chunk type (e.g., "fixed_size", "full_text").
        metadata: Optional metadata dict attached to each chunk.
        max_tokens: Maximum words per chunk.
        overlap: Number of overlapping words between consecutive chunks.

    Returns:
        List of Chunk objects. Empty list if text is empty.
    """
    if not text or not text.strip():
        return []

    chunk_metadata = metadata or {}
    words = text.split()

    # If the text fits in a single chunk, return it directly
    if len(words) <= max_tokens:
        return [Chunk(content=text.strip(), chunk_type=chunk_type, metadata=chunk_metadata)]

    chunks: list[Chunk] = []
    start = 0

    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        chunks.append(
            Chunk(content=chunk_text, chunk_type=chunk_type, metadata=chunk_metadata)
        )

        # Advance by (max_tokens - overlap) to create overlap with the next chunk
        start += max_tokens - overlap

    return chunks
