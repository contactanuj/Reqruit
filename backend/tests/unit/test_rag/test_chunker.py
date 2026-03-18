"""
Tests for document-aware chunking.

Verifies resume section splitting, job description splitting, fixed-size
fallback, and the internal section-splitting helper. All tests are
synchronous — the chunker is pure logic with no async I/O.
"""

import pytest

from src.rag.chunker import (
    RESUME_SECTIONS,
    Chunk,
    _split_by_sections,
    chunk_fixed_size,
    chunk_job_description,
    chunk_resume,
)

# ---------------------------------------------------------------------------
# Chunk dataclass
# ---------------------------------------------------------------------------


class TestChunkDataclass:
    def test_chunk_is_frozen(self):
        """Chunk instances are immutable (frozen dataclass)."""
        chunk = Chunk(content="test", chunk_type="skills", metadata={"id": "1"})
        with pytest.raises(AttributeError):
            chunk.content = "modified"  # type: ignore[misc]

    def test_chunk_stores_all_fields(self):
        """Chunk stores content, chunk_type, and metadata."""
        chunk = Chunk(content="Python dev", chunk_type="skills", metadata={"k": "v"})
        assert chunk.content == "Python dev"
        assert chunk.chunk_type == "skills"
        assert chunk.metadata == {"k": "v"}

    def test_chunk_default_metadata(self):
        """Chunk uses empty dict as default metadata."""
        chunk = Chunk(content="test", chunk_type="fixed_size")
        assert chunk.metadata == {}


# ---------------------------------------------------------------------------
# chunk_resume
# ---------------------------------------------------------------------------


class TestChunkResume:
    def test_splits_by_known_headings(self):
        """Resume with recognized headings is split into section chunks."""
        text = (
            "John Doe\nSoftware Engineer\n\n"
            "Education\nBS Computer Science, MIT\n\n"
            "Skills\nPython, FastAPI, MongoDB\n\n"
            "Experience\nBackend developer at Acme Corp for 3 years"
        )
        chunks = chunk_resume(text, "resume-1", "user-1")

        chunk_types = [c.chunk_type for c in chunks]
        assert "education" in chunk_types
        assert "skills" in chunk_types
        assert "work_experience" in chunk_types

    def test_preserves_section_content(self):
        """Content under each heading is correctly captured."""
        text = (
            "Skills\nPython, FastAPI, MongoDB\n\n"
            "Education\nBS Computer Science, MIT"
        )
        chunks = chunk_resume(text, "resume-1", "user-1")

        skills_chunk = next(c for c in chunks if c.chunk_type == "skills")
        assert "Python" in skills_chunk.content
        assert "FastAPI" in skills_chunk.content

    def test_attaches_metadata(self):
        """Each chunk carries resume_id and user_id in metadata."""
        text = "Education\nBS Computer Science"
        chunks = chunk_resume(text, "resume-42", "user-7")

        for chunk in chunks:
            assert chunk.metadata["resume_id"] == "resume-42"
            assert chunk.metadata["user_id"] == "user-7"

    def test_chunk_type_from_heading(self):
        """chunk_type is derived from the normalized heading name."""
        text = "Certifications\nAWS Solutions Architect"
        chunks = chunk_resume(text, "r1", "u1")

        assert any(c.chunk_type == "certifications" for c in chunks)

    def test_content_before_first_heading_is_preamble(self):
        """Text before the first recognized heading becomes a 'preamble' chunk."""
        text = (
            "John Doe — Senior Engineer\n\n"
            "Education\nBS Computer Science"
        )
        chunks = chunk_resume(text, "r1", "u1")

        assert chunks[0].chunk_type == "preamble"
        assert "John Doe" in chunks[0].content

    def test_falls_back_to_fixed_size(self):
        """Resume with no recognized headings falls back to fixed-size chunks."""
        text = "Just a plain paragraph with no section headings whatsoever."
        chunks = chunk_resume(text, "r1", "u1")

        assert len(chunks) >= 1
        # Fixed-size fallback produces "full_text" chunk type
        assert all(c.chunk_type == "full_text" for c in chunks)

    def test_empty_text_returns_empty(self):
        """Empty resume text returns no chunks."""
        assert chunk_resume("", "r1", "u1") == []
        assert chunk_resume("   ", "r1", "u1") == []

    def test_strips_whitespace_from_content(self):
        """Chunk content has leading/trailing whitespace stripped."""
        text = "Education\n\n   BS Computer Science, MIT   \n\n"
        chunks = chunk_resume(text, "r1", "u1")

        education_chunks = [c for c in chunks if c.chunk_type == "education"]
        assert len(education_chunks) == 1
        assert not education_chunks[0].content.startswith(" ")
        assert not education_chunks[0].content.endswith(" ")


# ---------------------------------------------------------------------------
# chunk_job_description
# ---------------------------------------------------------------------------


class TestChunkJobDescription:
    def test_splits_by_jd_headings(self):
        """JD with recognized headings is split into section chunks."""
        text = (
            "About\nWe are a fast-growing startup.\n\n"
            "Responsibilities\nBuild scalable backend services.\n\n"
            "Requirements\n5+ years of Python experience."
        )
        chunks = chunk_job_description(text, "job-1", "user-1")

        chunk_types = [c.chunk_type for c in chunks]
        assert "about" in chunk_types
        assert "responsibilities" in chunk_types
        assert "requirements" in chunk_types

    def test_attaches_job_metadata(self):
        """Each chunk carries job_id and user_id in metadata."""
        text = "Requirements\nPython experience required."
        chunks = chunk_job_description(text, "job-42", "user-7")

        for chunk in chunks:
            assert chunk.metadata["job_id"] == "job-42"
            assert chunk.metadata["user_id"] == "user-7"

    def test_falls_back_to_fixed_size(self):
        """JD with no recognized headings falls back to fixed-size chunks."""
        text = "Looking for a great developer to join our team."
        chunks = chunk_job_description(text, "j1", "u1")

        assert len(chunks) >= 1
        assert all(c.chunk_type == "full_text" for c in chunks)

    def test_empty_text_returns_empty(self):
        """Empty description returns no chunks."""
        assert chunk_job_description("", "j1", "u1") == []

    def test_about_section_recognized(self):
        """'About Us' and 'About the Company' headings are recognized."""
        text = "About Us\nWe build awesome things.\n\nRequirements\nPython"
        chunks = chunk_job_description(text, "j1", "u1")

        assert any(c.chunk_type == "about" for c in chunks)

    def test_multiple_heading_formats(self):
        """Different heading formats (markdown, colon, caps) are recognized."""
        # Markdown heading format
        text_md = "## Requirements\nPython experience"
        chunks_md = chunk_job_description(text_md, "j1", "u1")
        assert any(c.chunk_type == "requirements" for c in chunks_md)

        # Colon format
        text_colon = "Requirements:\nPython experience"
        chunks_colon = chunk_job_description(text_colon, "j1", "u1")
        assert any(c.chunk_type == "requirements" for c in chunks_colon)

        # Uppercase
        text_caps = "REQUIREMENTS\nPython experience"
        chunks_caps = chunk_job_description(text_caps, "j1", "u1")
        assert any(c.chunk_type == "requirements" for c in chunks_caps)


# ---------------------------------------------------------------------------
# chunk_fixed_size
# ---------------------------------------------------------------------------


class TestChunkFixedSize:
    def test_short_text_single_chunk(self):
        """Text below max_tokens produces a single chunk."""
        text = "A short piece of text."
        chunks = chunk_fixed_size(text, max_tokens=500)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_long_text_multiple_chunks(self):
        """Text exceeding max_tokens is split into multiple chunks."""
        # 100 words, max_tokens=10 -> should produce multiple chunks
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunk_fixed_size(text, max_tokens=10, overlap=2)

        assert len(chunks) > 1

    def test_overlap_between_chunks(self):
        """Adjacent chunks share overlapping tokens."""
        words = [f"word{i}" for i in range(20)]
        text = " ".join(words)
        chunks = chunk_fixed_size(text, max_tokens=10, overlap=3)

        # Second chunk should start 7 words in (10 - 3 overlap)
        first_words = chunks[0].content.split()
        second_words = chunks[1].content.split()

        # The last 3 words of chunk 0 should appear at the start of chunk 1
        assert first_words[-3:] == second_words[:3]

    def test_custom_max_tokens_and_overlap(self):
        """Non-default max_tokens and overlap are respected."""
        words = [f"w{i}" for i in range(50)]
        text = " ".join(words)
        chunks = chunk_fixed_size(text, max_tokens=20, overlap=5)

        # Each chunk should have at most 20 words
        for chunk in chunks:
            assert len(chunk.content.split()) <= 20

    def test_empty_text_returns_empty(self):
        """Empty text returns no chunks."""
        assert chunk_fixed_size("") == []
        assert chunk_fixed_size("   ") == []

    def test_chunk_type_passed_through(self):
        """Custom chunk_type is used for all chunks."""
        chunks = chunk_fixed_size("Some text.", chunk_type="notes")
        assert all(c.chunk_type == "notes" for c in chunks)

    def test_metadata_passed_through(self):
        """Custom metadata is attached to all chunks."""
        meta = {"source": "manual", "user_id": "u1"}
        chunks = chunk_fixed_size("Some text.", metadata=meta)
        assert all(c.metadata == meta for c in chunks)


# ---------------------------------------------------------------------------
# _split_by_sections (internal helper)
# ---------------------------------------------------------------------------


class TestSplitBySections:
    def test_returns_section_name_and_content_pairs(self):
        """Returns list of (section_name, content) tuples."""
        text = "Education\nBS Computer Science\n\nSkills\nPython, Java"
        sections = _split_by_sections(text, RESUME_SECTIONS)

        names = [name for name, _ in sections]
        assert "education" in names
        assert "skills" in names

    def test_no_matching_sections_returns_empty(self):
        """Returns empty list when no headings match."""
        text = "Just some random text without any section headings."
        sections = _split_by_sections(text, RESUME_SECTIONS)

        assert sections == []

    def test_content_before_first_heading_included_as_preamble(self):
        """Content before the first heading is returned as 'preamble'."""
        text = "John Doe\nSoftware Engineer\n\nEducation\nBS CS"
        sections = _split_by_sections(text, RESUME_SECTIONS)

        assert sections[0][0] == "preamble"
        assert "John Doe" in sections[0][1]
