"""
STAR story document model — behavioral interview story bank.

STAR (Situation, Task, Action, Result) stories are the foundation of
behavioral interview preparation. The STARHelper agent helps users craft
and refine stories from their experience. These stories are embedded in
Weaviate for semantic retrieval — when a behavioral question is asked,
the most relevant story is fetched by similarity matching.

Design decisions
----------------
Why a dedicated collection (not embedded in Profile):
    A user can accumulate dozens of STAR stories over time. Embedding them
    in Profile would make the profile document large and slow to load.
    A separate collection lets us query stories by tags, paginate results,
    and maintain independent lifecycle (create, edit, delete individual
    stories).

Why tags field:
    Tags enable categorical retrieval: "leadership", "conflict resolution",
    "technical challenge". The STARHelper agent auto-generates tags based
    on story content. Combined with Weaviate's semantic search, tags
    provide a dual retrieval strategy — exact tag match for known
    categories, semantic search for novel interview questions.

Why an index on tags:
    MongoDB's multikey index on array fields enables efficient queries
    like {"tags": "leadership"} without scanning the entire collection.
"""

from beanie import Indexed, PydanticObjectId
from pymongo import ASCENDING, IndexModel

from src.db.base_document import TimestampedDocument


class STARStory(TimestampedDocument):
    """
    Behavioral interview story in STAR format.

    Fields:
        user_id: Owner of this story.
        title: Short descriptive title (e.g., "Led database migration project").
        situation: Context and background of the scenario.
        task: What was the specific challenge or responsibility.
        action: Steps taken to address the situation.
        result: Outcome, ideally with quantifiable impact.
        tags: Categorical tags for retrieval (e.g., ["leadership", "databases"]).
    """

    user_id: Indexed(PydanticObjectId)
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    tags: list[str] = []

    class Settings:
        name = "star_stories"
        indexes = [
            IndexModel(
                [("tags", ASCENDING)],
                name="tags_idx",
            ),
        ]
