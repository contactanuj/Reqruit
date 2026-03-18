"""
Tests for the NegotiationSession document model.
"""

from beanie import PydanticObjectId

from src.db.documents.negotiation_session import NegotiationSession


class TestNegotiationSession:

    def test_collection_name(self):
        assert NegotiationSession.Settings.name == "negotiation_sessions"

    def test_create_with_required_fields(self):
        session = NegotiationSession(
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
            offer_id=PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
            session_type="simulation",
        )
        assert session.session_type == "simulation"
        assert session.status == "active"
        assert session.thread_id == ""
        assert session.transcript == []
        assert session.scripts == []
        assert session.decision_matrix == {}

    def test_create_with_all_fields(self):
        session = NegotiationSession(
            user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
            offer_id=PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
            session_type="script",
            status="completed",
            thread_id="thread-123",
            transcript=[{"role": "recruiter", "content": "Hello"}],
            scripts=[{"opening": "Hi"}],
            decision_matrix={"recommended": "A"},
        )
        assert session.status == "completed"
        assert session.thread_id == "thread-123"
        assert len(session.transcript) == 1
        assert len(session.scripts) == 1
        assert session.decision_matrix["recommended"] == "A"

    def test_indexes_defined(self):
        indexes = NegotiationSession.Settings.indexes
        assert len(indexes) >= 1
        # First index should be (user_id, created_at desc)
        first_index = indexes[0]
        field_names = [f[0] for f in first_index]
        assert "user_id" in field_names
        assert "created_at" in field_names

    def test_session_types(self):
        for stype in ("simulation", "script", "decision"):
            session = NegotiationSession(
                user_id=PydanticObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
                offer_id=PydanticObjectId("bbbbbbbbbbbbbbbbbbbbbbbb"),
                session_type=stype,
            )
            assert session.session_type == stype

    def test_registered_in_all_document_models(self):
        from src.db.documents import ALL_DOCUMENT_MODELS

        assert NegotiationSession in ALL_DOCUMENT_MODELS
