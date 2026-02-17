"""
Base document class with automatic timestamps for all MongoDB collections.

Design decisions
----------------
Why a custom base class (not using Beanie's Document directly):
    Beanie does not provide built-in timestamp fields. Every production
    application needs created_at and updated_at for auditing, debugging,
    and data lifecycle management. Rather than adding these fields to each
    of the 12 document models individually, we define them once here.

    Alternative: add created_at/updated_at to each document model manually.
    Works but violates DRY — any change to timestamp behavior requires
    editing 12 files.

How timestamps work with Beanie event hooks:
    Beanie provides @before_event decorators that run before database
    operations. We use:
    - @before_event(Insert): sets both created_at and updated_at on first save
    - @before_event(Replace, Save): updates only updated_at on modifications

    This is the Beanie equivalent of SQLAlchemy's server_default and
    onupdate. The hooks run in application code, not in MongoDB itself.

    Alternative: set timestamps in MongoDB using $currentDate or
    server-side defaults. This offloads the work to the database but
    requires raw MongoDB operations and bypasses Beanie's ODM layer.

Why schema_version field:
    MongoDB is schema-less — adding a new field to a document model does
    not require a migration. Old documents simply lack the new field. But
    for breaking changes (renaming a field, changing a type), we need to
    know which schema version a document was written with.

    The schema_version field is set to 1 by default. Migration scripts
    can query documents by version and transform them in place. This is
    the Schema Versioning pattern recommended by MongoDB Inc. and used
    in production at companies like Uber and Lyft.

Usage
-----
    from src.db.base_document import TimestampedDocument

    class User(TimestampedDocument):
        email: str
        hashed_password: str

        class Settings:
            name = "users"
"""

from datetime import UTC, datetime

from beanie import Document, Insert, Replace, Save, before_event


class TimestampedDocument(Document):
    """
    Base document with automatic timestamps and schema versioning.

    All 12 MongoDB collections inherit from this class. Provides:
    - created_at: set once on insert, never modified after
    - updated_at: set on insert, refreshed on every save/replace
    - schema_version: tracks document schema for future migrations

    This class is never registered with init_beanie directly — only
    concrete subclasses (User, Job, etc.) are registered.
    """

    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1

    @before_event(Insert)
    def set_created_at(self) -> None:
        """Set both timestamps on first insert."""
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now

    @before_event(Replace, Save)
    def set_updated_at(self) -> None:
        """Refresh the modification timestamp on save or replace."""
        self.updated_at = datetime.now(UTC)
