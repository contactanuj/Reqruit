"""Tests for the Beanie migration framework — base class and runner."""

from unittest.mock import AsyncMock, MagicMock

from src.db.migrations.base import Migration
from src.db.migrations.runner import MigrationRunner

# -- Concrete test migration --------------------------------------------------


class RenameFieldMigration(Migration):
    collection_name = "users"
    from_version = 1
    to_version = 2
    description = "Rename full_name to display_name"

    async def up(self, document: dict) -> dict:
        document["display_name"] = document.pop("full_name", "")
        return document

    async def down(self, document: dict) -> dict:
        document["full_name"] = document.pop("display_name", "")
        return document


class AddFieldMigration(Migration):
    collection_name = "users"
    from_version = 2
    to_version = 3
    description = "Add timezone field"

    async def up(self, document: dict) -> dict:
        document["timezone"] = document.get("timezone", "UTC")
        return document

    async def down(self, document: dict) -> dict:
        document.pop("timezone", None)
        return document


class JobMigration(Migration):
    collection_name = "jobs"
    from_version = 1
    to_version = 2
    description = "Normalize salary to USD"

    async def up(self, document: dict) -> dict:
        document["salary_currency"] = "USD"
        return document

    async def down(self, document: dict) -> dict:
        document.pop("salary_currency", None)
        return document


# -- Base Migration tests ------------------------------------------------------


class TestMigrationBase:
    def test_repr(self):
        m = RenameFieldMigration()
        r = repr(m)
        assert "users" in r
        assert "v1→v2" in r
        assert "Rename full_name" in r

    async def test_up_transforms_document(self):
        m = RenameFieldMigration()
        doc = {"full_name": "Alice", "email": "alice@example.com"}
        result = await m.up(doc)
        assert result["display_name"] == "Alice"
        assert "full_name" not in result

    async def test_down_reverses_transform(self):
        m = RenameFieldMigration()
        doc = {"display_name": "Alice", "email": "alice@example.com"}
        result = await m.down(doc)
        assert result["full_name"] == "Alice"
        assert "display_name" not in result


# -- MigrationRunner tests -----------------------------------------------------


def _make_mock_db():
    """Create a mock Motor database with collection support."""
    db = MagicMock()
    collections = {}

    def get_collection(name):
        if name not in collections:
            col = MagicMock()
            col.find_one = AsyncMock(return_value=None)
            col.insert_one = AsyncMock()
            col.delete_one = AsyncMock()
            col.replace_one = AsyncMock()
            # find() returns an async iterator
            col.find = MagicMock(return_value=AsyncIter([]))
            collections[name] = col
        return collections[name]

    db.__getitem__ = MagicMock(side_effect=get_collection)

    # Mock transaction support: db.client.start_session() -> async ctx manager
    mock_session = MagicMock()
    mock_session.start_transaction = MagicMock(
        return_value=MagicMock(__aenter__=AsyncMock(), __aexit__=AsyncMock())
    )
    mock_session_ctx = MagicMock(
        __aenter__=AsyncMock(return_value=mock_session),
        __aexit__=AsyncMock(),
    )
    db.client = MagicMock()
    db.client.start_session = AsyncMock(return_value=mock_session_ctx)

    # Pre-create common collections so tests can configure them
    get_collection("_migrations")
    return db, get_collection


class AsyncIter:  # noqa: N801
    """Helper to make a list behave as an async iterator."""

    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


class TestMigrationRunner:
    def test_register_and_sort(self):
        db, _ = _make_mock_db()
        runner = MigrationRunner(db)
        m2 = AddFieldMigration()
        m1 = RenameFieldMigration()
        runner.register(m2)
        runner.register(m1)
        sorted_migrations = runner._sorted_migrations()
        assert sorted_migrations[0].from_version == 1
        assert sorted_migrations[1].from_version == 2

    async def test_run_applies_migrations(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())

        # Set up the users collection to return one document
        doc = {"_id": "abc", "full_name": "Alice", "schema_version": 1}
        get_col("users").find = MagicMock(return_value=AsyncIter([doc]))

        result = await runner.run(direction="up")

        assert result["direction"] == "up"
        assert len(result["migrations"]) == 1
        assert result["migrations"][0]["status"] == "applied"
        assert result["migrations"][0]["documents_affected"] == 1
        get_col("users").replace_one.assert_awaited_once()

    async def test_skips_already_applied(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())

        # Migration already recorded
        get_col("_migrations").find_one = AsyncMock(return_value={"_id": "existing"})

        result = await runner.run(direction="up")

        assert result["migrations"][0]["status"] == "skipped"
        assert result["migrations"][0]["documents_affected"] == 0

    async def test_run_down_reverses(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())

        doc = {"_id": "abc", "display_name": "Alice", "schema_version": 2}
        get_col("users").find = MagicMock(return_value=AsyncIter([doc]))

        result = await runner.run(direction="down")

        assert result["direction"] == "down"
        assert result["migrations"][0]["documents_affected"] == 1
        # Down should delete the migration record
        get_col("_migrations").delete_one.assert_awaited_once()

    async def test_run_no_matching_documents(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())

        # No documents match version filter
        get_col("users").find = MagicMock(return_value=AsyncIter([]))

        result = await runner.run(direction="up")

        assert result["migrations"][0]["documents_affected"] == 0

    async def test_multiple_collections(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())
        runner.register(JobMigration())

        user_doc = {"_id": "u1", "full_name": "Bob", "schema_version": 1}
        job_doc = {"_id": "j1", "title": "Engineer", "schema_version": 1}

        get_col("users").find = MagicMock(return_value=AsyncIter([user_doc]))
        get_col("jobs").find = MagicMock(return_value=AsyncIter([job_doc]))

        result = await runner.run(direction="up")

        assert len(result["migrations"]) == 2
        # Sorted: jobs (from_version=1) before users (from_version=1) alphabetically
        total_affected = sum(m["documents_affected"] for m in result["migrations"])
        assert total_affected == 2

    async def test_version_updated_on_replace(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())

        doc = {"_id": "abc", "full_name": "Alice", "schema_version": 1}
        get_col("users").find = MagicMock(return_value=AsyncIter([doc]))

        await runner.run(direction="up")

        replaced_doc = get_col("users").replace_one.call_args[0][1]
        assert replaced_doc["schema_version"] == 2

    async def test_records_migration_on_up(self):
        db, get_col = _make_mock_db()
        runner = MigrationRunner(db)
        runner.register(RenameFieldMigration())
        get_col("users").find = MagicMock(return_value=AsyncIter([]))

        await runner.run(direction="up")

        get_col("_migrations").insert_one.assert_awaited_once()
        record = get_col("_migrations").insert_one.call_args[0][0]
        assert record["collection_name"] == "users"
        assert record["from_version"] == 1
        assert record["to_version"] == 2
