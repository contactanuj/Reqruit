"""
NegotiationSession — tracks negotiation workflow sessions for a user.

Stores session metadata (type, status) and results (transcript, scripts,
decision matrix) for retrieval, listing, and deletion.
"""

from beanie import Indexed, PydanticObjectId

from src.db.base_document import TimestampedDocument


class NegotiationSession(TimestampedDocument):
    """A negotiation workflow session (simulation, script, or decision)."""

    user_id: Indexed(PydanticObjectId)  # type: ignore[valid-type]
    offer_id: PydanticObjectId
    session_type: str  # simulation, script, decision
    status: str = "active"  # active, completed, abandoned
    thread_id: str = ""  # LangGraph checkpoint thread ID

    # Results — populated based on session_type
    transcript: list[dict] = []  # simulation turns
    scripts: list[dict] = []  # script generation output
    decision_matrix: dict = {}  # decision framework output

    class Settings:
        name = "negotiation_sessions"
        indexes = [
            [("user_id", 1), ("created_at", -1)],
        ]
