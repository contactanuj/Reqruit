"""
Unit test configuration — patches Beanie internals for document instantiation.

Why this file is needed
-----------------------
Beanie 2.0's Document.__init__ verifies that init_beanie() has been called
by checking _document_settings on the class. Without a MongoDB connection,
constructing any Document subclass raises CollectionWasNotInitialized.

This is correct behavior for production — you should never create documents
without a database connection. But in unit tests, we specifically want to
test model schemas, defaults, and validation WITHOUT a database.

The autouse fixture below mocks _document_settings on all 12 document
classes before each test, allowing construction to succeed. The mock is
cleaned up after each test automatically.

Alternative approaches considered:
    1. Use model_construct() — bypasses __init__, but also bypasses Pydantic
       validation. We want to test that validation works correctly.
    2. Run init_beanie() with a mock database — heavier setup, and creates
       a coupling between unit tests and Beanie's init internals.
    3. Use mongomock or mongomock-motor — adds a test dependency and is
       closer to integration testing than unit testing.

The monkeypatch approach is the lightest and most targeted. It patches
only the specific check that prevents construction, leaving all Pydantic
validation intact.

Integration tests (tests/integration/) use a real MongoDB instance via
Docker and do NOT need this fixture.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_beanie_document_settings():
    """
    Allow Beanie Document subclasses to be instantiated without init_beanie().

    Mocks _document_settings (which holds the collection reference, indexes,
    and other Beanie internals) on all 12 document classes. This prevents
    CollectionWasNotInitialized without affecting Pydantic model behavior.
    """
    from src.db.documents import ALL_DOCUMENT_MODELS

    originals = {}
    for model in ALL_DOCUMENT_MODELS:
        originals[model] = getattr(model, "_document_settings", None)
        model._document_settings = MagicMock()

    yield

    # Restore original values to avoid cross-test contamination.
    for model, original in originals.items():
        model._document_settings = original
