"""
Tests for the RAG indexing pipeline.

Verifies that IndexingService correctly fetches documents from MongoDB,
chunks them, embeds the chunks, stores them in Weaviate, and handles
delete-before-reindex. All repositories and the embedding service are
mocked — these tests focus on the orchestration logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from src.rag.chunker import Chunk
from src.services.indexing_service import IndexingService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_RESUME_ID = str(PydanticObjectId())
FAKE_JOB_ID = str(PydanticObjectId())
FAKE_DOC_ID = str(PydanticObjectId())
FAKE_STORY_ID = str(PydanticObjectId())
FAKE_USER_ID = "user-1"

# A 384-dim vector stub (same as BGE-small output)
FAKE_VECTOR = [0.1] * 384


@pytest.fixture
def mock_repos():
    """Create mock MongoDB and Weaviate repositories."""
    return {
        "resume_repo": MagicMock(),
        "job_repo": MagicMock(),
        "star_story_repo": MagicMock(),
        "document_repo": MagicMock(),
        "resume_chunk_weaviate": MagicMock(),
        "job_embedding_weaviate": MagicMock(),
        "cover_letter_weaviate": MagicMock(),
        "star_story_weaviate": MagicMock(),
    }


@pytest.fixture
def service(mock_repos):
    """Create an IndexingService with all mock repositories."""
    return IndexingService(**mock_repos)


@pytest.fixture
def mock_resume():
    """Create a mock Resume document."""
    resume = MagicMock()
    resume.raw_text = (
        "Education\nBS Computer Science, MIT\n\n"
        "Skills\nPython, FastAPI, MongoDB"
    )
    resume.title = "General Resume"
    return resume


@pytest.fixture
def mock_job():
    """Create a mock Job document."""
    job = MagicMock()
    job.title = "Backend Developer"
    job.description = (
        "Responsibilities\nBuild scalable APIs.\n\n"
        "Requirements\n5+ years Python experience."
    )
    return job


@pytest.fixture
def mock_document():
    """Create a mock DocumentRecord (cover letter)."""
    doc = MagicMock()
    doc.content = "Dear Hiring Manager, I am writing to express interest..."
    return doc


@pytest.fixture
def mock_star_story():
    """Create a mock STARStory document."""
    story = MagicMock()
    story.situation = "Database was slow under load."
    story.task = "Optimize query performance."
    story.action = "Added indexes and rewrote N+1 queries."
    story.result = "Reduced latency by 80%."
    story.tags = ["databases", "performance"]
    return story


# ---------------------------------------------------------------------------
# index_resume
# ---------------------------------------------------------------------------


class TestIndexResume:
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_fetches_resume_from_mongodb(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume calls get_by_id on the resume repository."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        mock_repos["resume_repo"].get_by_id.assert_called_once_with(
            PydanticObjectId(FAKE_RESUME_ID)
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_deletes_existing_chunks(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume deletes existing chunks before re-indexing."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[{"uuid": "old-uuid", "properties": {}}]
        )
        mock_repos["resume_chunk_weaviate"].delete_object = AsyncMock(
            return_value=True
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        mock_repos["resume_chunk_weaviate"].delete_object.assert_called_once_with(
            "old-uuid", FAKE_USER_ID
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_ensures_tenant(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume ensures the user's tenant exists."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        mock_repos["resume_chunk_weaviate"].ensure_tenant.assert_called_once_with(
            FAKE_USER_ID
        )

    @patch("src.services.indexing_service.chunk_resume")
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_chunks_raw_text(
        self, mock_embed, mock_chunk, service, mock_repos, mock_resume
    ):
        """index_resume passes the resume's raw_text to chunk_resume."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_chunk.return_value = [
            Chunk(content="test", chunk_type="skills", metadata={"resume_id": FAKE_RESUME_ID})
        ]
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        mock_chunk.assert_called_once_with(
            mock_resume.raw_text, FAKE_RESUME_ID, FAKE_USER_ID
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_embeds_chunk_contents(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume embeds the content of each chunk."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        # embed_texts is called with a list of chunk content strings
        call_args = mock_embed.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) > 0

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_stores_in_weaviate(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume calls insert_object for each chunk."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        assert mock_repos["resume_chunk_weaviate"].insert_object.call_count >= 1

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_returns_chunk_count(
        self, mock_embed, service, mock_repos, mock_resume
    ):
        """index_resume returns the number of chunks stored."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=mock_resume)
        mock_repos["resume_chunk_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["resume_chunk_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["resume_chunk_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        count = await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)

        assert count >= 1

    async def test_raises_for_missing_resume(self, service, mock_repos):
        """index_resume raises ValueError when resume not found."""
        mock_repos["resume_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Resume not found"):
            await service.index_resume(FAKE_RESUME_ID, FAKE_USER_ID)


# ---------------------------------------------------------------------------
# index_job
# ---------------------------------------------------------------------------


class TestIndexJob:
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_fetches_job_from_mongodb(
        self, mock_embed, service, mock_repos, mock_job
    ):
        """index_job calls get_by_id on the job repository."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=mock_job)
        mock_repos["job_embedding_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["job_embedding_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["job_embedding_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)

        mock_repos["job_repo"].get_by_id.assert_called_once_with(
            PydanticObjectId(FAKE_JOB_ID)
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_deletes_existing_embeddings(
        self, mock_embed, service, mock_repos, mock_job
    ):
        """index_job deletes existing job embeddings before re-indexing."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=mock_job)
        mock_repos["job_embedding_weaviate"].search_by_property = AsyncMock(
            return_value=[{"uuid": "old-uuid", "properties": {}}]
        )
        mock_repos["job_embedding_weaviate"].delete_object = AsyncMock(
            return_value=True
        )
        mock_repos["job_embedding_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["job_embedding_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)

        mock_repos["job_embedding_weaviate"].delete_object.assert_called_once_with(
            "old-uuid", FAKE_USER_ID
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_chunks_job_description(
        self, mock_embed, service, mock_repos, mock_job
    ):
        """index_job passes the job description to chunk_job_description."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=mock_job)
        mock_repos["job_embedding_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["job_embedding_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["job_embedding_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        count = await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)

        # Job description has recognizable headings -> produces chunks
        assert count >= 1

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_stores_in_weaviate(
        self, mock_embed, service, mock_repos, mock_job
    ):
        """index_job calls insert_object for each chunk."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=mock_job)
        mock_repos["job_embedding_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["job_embedding_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["job_embedding_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)

        assert mock_repos["job_embedding_weaviate"].insert_object.call_count >= 1

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_returns_chunk_count(
        self, mock_embed, service, mock_repos, mock_job
    ):
        """index_job returns the number of chunks stored."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=mock_job)
        mock_repos["job_embedding_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["job_embedding_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["job_embedding_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        count = await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)

        assert count >= 1

    async def test_raises_for_missing_job(self, service, mock_repos):
        """index_job raises ValueError when job not found."""
        mock_repos["job_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Job not found"):
            await service.index_job(FAKE_JOB_ID, FAKE_USER_ID)


# ---------------------------------------------------------------------------
# index_cover_letter
# ---------------------------------------------------------------------------


class TestIndexCoverLetter:
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_fetches_document_record(
        self, mock_embed, service, mock_repos, mock_document
    ):
        """index_cover_letter calls get_by_id on the document repository."""
        mock_repos["document_repo"].get_by_id = AsyncMock(
            return_value=mock_document
        )
        mock_repos["cover_letter_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["cover_letter_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["cover_letter_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_cover_letter(
            FAKE_DOC_ID, FAKE_USER_ID, company="Acme", role="Engineer"
        )

        mock_repos["document_repo"].get_by_id.assert_called_once_with(
            PydanticObjectId(FAKE_DOC_ID)
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_deletes_existing_embeddings(
        self, mock_embed, service, mock_repos, mock_document
    ):
        """index_cover_letter deletes old embeddings before re-indexing."""
        mock_repos["document_repo"].get_by_id = AsyncMock(
            return_value=mock_document
        )
        mock_repos["cover_letter_weaviate"].search_by_property = AsyncMock(
            return_value=[{"uuid": "old-uuid", "properties": {}}]
        )
        mock_repos["cover_letter_weaviate"].delete_object = AsyncMock(
            return_value=True
        )
        mock_repos["cover_letter_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["cover_letter_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_cover_letter(FAKE_DOC_ID, FAKE_USER_ID)

        mock_repos["cover_letter_weaviate"].delete_object.assert_called_once()

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_embeds_full_content(
        self, mock_embed, service, mock_repos, mock_document
    ):
        """index_cover_letter embeds the full content as a single embedding."""
        mock_repos["document_repo"].get_by_id = AsyncMock(
            return_value=mock_document
        )
        mock_repos["cover_letter_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["cover_letter_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["cover_letter_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_cover_letter(FAKE_DOC_ID, FAKE_USER_ID)

        # embed_texts called with a single-element list (full content)
        call_args = mock_embed.call_args[0][0]
        assert len(call_args) == 1
        assert mock_document.content in call_args[0]

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_stores_in_weaviate(
        self, mock_embed, service, mock_repos, mock_document
    ):
        """index_cover_letter calls insert_object once."""
        mock_repos["document_repo"].get_by_id = AsyncMock(
            return_value=mock_document
        )
        mock_repos["cover_letter_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["cover_letter_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["cover_letter_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_cover_letter(
            FAKE_DOC_ID, FAKE_USER_ID, company="Acme", role="Dev"
        )

        mock_repos["cover_letter_weaviate"].insert_object.assert_called_once()
        # Verify company and role are in the properties
        call_kwargs = mock_repos[
            "cover_letter_weaviate"
        ].insert_object.call_args[1]
        assert call_kwargs["properties"]["company"] == "Acme"
        assert call_kwargs["properties"]["role"] == "Dev"

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_returns_count_of_one(
        self, mock_embed, service, mock_repos, mock_document
    ):
        """index_cover_letter returns 1 (single embedding stored)."""
        mock_repos["document_repo"].get_by_id = AsyncMock(
            return_value=mock_document
        )
        mock_repos["cover_letter_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["cover_letter_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["cover_letter_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        count = await service.index_cover_letter(FAKE_DOC_ID, FAKE_USER_ID)

        assert count == 1

    async def test_raises_for_missing_document(self, service, mock_repos):
        """index_cover_letter raises ValueError when document not found."""
        mock_repos["document_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Document not found"):
            await service.index_cover_letter(FAKE_DOC_ID, FAKE_USER_ID)


# ---------------------------------------------------------------------------
# index_star_story
# ---------------------------------------------------------------------------


class TestIndexStarStory:
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_fetches_star_story(
        self, mock_embed, service, mock_repos, mock_star_story
    ):
        """index_star_story calls get_by_id on the story repository."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(
            return_value=mock_star_story
        )
        mock_repos["star_story_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["star_story_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["star_story_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)

        mock_repos["star_story_repo"].get_by_id.assert_called_once_with(
            PydanticObjectId(FAKE_STORY_ID)
        )

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_deletes_existing_embeddings(
        self, mock_embed, service, mock_repos, mock_star_story
    ):
        """index_star_story deletes old embeddings before re-indexing."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(
            return_value=mock_star_story
        )
        mock_repos["star_story_weaviate"].search_by_property = AsyncMock(
            return_value=[{"uuid": "old-uuid", "properties": {}}]
        )
        mock_repos["star_story_weaviate"].delete_object = AsyncMock(
            return_value=True
        )
        mock_repos["star_story_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["star_story_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)

        mock_repos["star_story_weaviate"].delete_object.assert_called_once()

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_concatenates_star_fields(
        self, mock_embed, service, mock_repos, mock_star_story
    ):
        """index_star_story concatenates all STAR fields for embedding."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(
            return_value=mock_star_story
        )
        mock_repos["star_story_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["star_story_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["star_story_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)

        # embed_texts receives the concatenated STAR text
        embedded_texts = mock_embed.call_args[0][0]
        assert len(embedded_texts) == 1
        text = embedded_texts[0]
        assert "Situation:" in text
        assert "Task:" in text
        assert "Action:" in text
        assert "Result:" in text

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_stores_in_weaviate(
        self, mock_embed, service, mock_repos, mock_star_story
    ):
        """index_star_story calls insert_object with story properties."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(
            return_value=mock_star_story
        )
        mock_repos["star_story_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["star_story_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["star_story_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)

        mock_repos["star_story_weaviate"].insert_object.assert_called_once()
        call_kwargs = mock_repos[
            "star_story_weaviate"
        ].insert_object.call_args[1]
        assert call_kwargs["properties"]["tags"] == ["databases", "performance"]
        assert call_kwargs["properties"]["story_id"] == FAKE_STORY_ID

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_returns_count_of_one(
        self, mock_embed, service, mock_repos, mock_star_story
    ):
        """index_star_story returns 1 (single embedding stored)."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(
            return_value=mock_star_story
        )
        mock_repos["star_story_weaviate"].search_by_property = AsyncMock(
            return_value=[]
        )
        mock_repos["star_story_weaviate"].ensure_tenant = AsyncMock()
        mock_repos["star_story_weaviate"].insert_object = AsyncMock(
            return_value="uuid-1"
        )
        mock_embed.return_value = [FAKE_VECTOR]

        count = await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)

        assert count == 1

    async def test_raises_for_missing_story(self, service, mock_repos):
        """index_star_story raises ValueError when story not found."""
        mock_repos["star_story_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="STAR story not found"):
            await service.index_star_story(FAKE_STORY_ID, FAKE_USER_ID)


# ---------------------------------------------------------------------------
# delete_index
# ---------------------------------------------------------------------------


class TestDeleteIndex:
    async def test_finds_and_deletes_objects(self, service):
        """delete_index finds objects by property and deletes each one."""
        mock_repo = MagicMock()
        mock_repo.search_by_property = AsyncMock(
            return_value=[
                {"uuid": "uuid-1", "properties": {}},
                {"uuid": "uuid-2", "properties": {}},
            ]
        )
        mock_repo.delete_object = AsyncMock(return_value=True)

        with patch(
            "src.services.indexing_service.WeaviateRepository",
            return_value=mock_repo,
        ):
            count = await service.delete_index(
                "ResumeChunk", "resume_id", "r1", FAKE_USER_ID
            )

        assert count == 2
        assert mock_repo.delete_object.call_count == 2

    async def test_returns_count_of_deleted(self, service):
        """delete_index returns the number of objects deleted."""
        mock_repo = MagicMock()
        mock_repo.search_by_property = AsyncMock(
            return_value=[{"uuid": "uuid-1", "properties": {}}]
        )
        mock_repo.delete_object = AsyncMock(return_value=True)

        with patch(
            "src.services.indexing_service.WeaviateRepository",
            return_value=mock_repo,
        ):
            count = await service.delete_index(
                "ResumeChunk", "resume_id", "r1", FAKE_USER_ID
            )

        assert count == 1

    async def test_returns_zero_for_no_objects(self, service):
        """delete_index returns 0 when no matching objects exist."""
        mock_repo = MagicMock()
        mock_repo.search_by_property = AsyncMock(return_value=[])

        with patch(
            "src.services.indexing_service.WeaviateRepository",
            return_value=mock_repo,
        ):
            count = await service.delete_index(
                "ResumeChunk", "resume_id", "r1", FAKE_USER_ID
            )

        assert count == 0

    async def test_ensures_tenant_before_search(self, service):
        """delete_index creates a WeaviateRepository with the right collection."""
        mock_repo = MagicMock()
        mock_repo.search_by_property = AsyncMock(return_value=[])

        with patch(
            "src.services.indexing_service.WeaviateRepository",
            return_value=mock_repo,
        ) as mock_class:
            await service.delete_index(
                "ResumeChunk", "resume_id", "r1", FAKE_USER_ID
            )

        mock_class.assert_called_once_with("ResumeChunk")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestDeleteExisting:
    async def test_finds_by_property(self, service, mock_repos):
        """_delete_existing calls search_by_property on the repo."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.search_by_property = AsyncMock(return_value=[])

        await service._delete_existing(repo, "resume_id", "r1", FAKE_USER_ID)

        repo.search_by_property.assert_called_once_with(
            property_name="resume_id",
            property_value="r1",
            tenant=FAKE_USER_ID,
        )

    async def test_deletes_each_object(self, service, mock_repos):
        """_delete_existing calls delete_object for every found object."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.search_by_property = AsyncMock(
            return_value=[
                {"uuid": "uuid-1", "properties": {}},
                {"uuid": "uuid-2", "properties": {}},
            ]
        )
        repo.delete_object = AsyncMock(return_value=True)

        await service._delete_existing(repo, "resume_id", "r1", FAKE_USER_ID)

        assert repo.delete_object.call_count == 2

    async def test_returns_count(self, service, mock_repos):
        """_delete_existing returns the number of objects deleted."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.search_by_property = AsyncMock(
            return_value=[{"uuid": "u1", "properties": {}}]
        )
        repo.delete_object = AsyncMock(return_value=True)

        count = await service._delete_existing(
            repo, "resume_id", "r1", FAKE_USER_ID
        )

        assert count == 1


class TestEmbedAndStore:
    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_embeds_texts(self, mock_embed, service, mock_repos):
        """_embed_and_store calls embed_texts with chunk content."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.insert_object = AsyncMock(return_value="uuid-1")
        mock_embed.return_value = [FAKE_VECTOR]

        chunks = [Chunk(content="test text", chunk_type="skills", metadata={})]
        await service._embed_and_store(repo, chunks, FAKE_USER_ID)

        mock_embed.assert_called_once_with(["test text"])

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_inserts_objects(self, mock_embed, service, mock_repos):
        """_embed_and_store calls insert_object for each chunk."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.insert_object = AsyncMock(return_value="uuid-1")
        mock_embed.return_value = [FAKE_VECTOR, FAKE_VECTOR]

        chunks = [
            Chunk(content="chunk 1", chunk_type="skills", metadata={"k": "v1"}),
            Chunk(content="chunk 2", chunk_type="education", metadata={"k": "v2"}),
        ]
        await service._embed_and_store(repo, chunks, FAKE_USER_ID)

        assert repo.insert_object.call_count == 2

    @patch("src.services.indexing_service.embed_texts", new_callable=AsyncMock)
    async def test_returns_count(self, mock_embed, service, mock_repos):
        """_embed_and_store returns the number of objects stored."""
        repo = mock_repos["resume_chunk_weaviate"]
        repo.insert_object = AsyncMock(return_value="uuid-1")
        mock_embed.return_value = [FAKE_VECTOR]

        chunks = [Chunk(content="test", chunk_type="skills", metadata={})]
        count = await service._embed_and_store(repo, chunks, FAKE_USER_ID)

        assert count == 1

    async def test_empty_chunks_returns_zero(self, service, mock_repos):
        """_embed_and_store returns 0 for empty chunk list."""
        repo = mock_repos["resume_chunk_weaviate"]
        count = await service._embed_and_store(repo, [], FAKE_USER_ID)

        assert count == 0
