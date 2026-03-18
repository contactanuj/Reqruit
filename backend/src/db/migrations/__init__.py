"""
Beanie migration framework — versioned schema migrations for MongoDB.

Provides a base Migration class and a runner that discovers and executes
migrations in order. Each migration targets a specific collection and
schema version transition.
"""

from src.db.migrations.base import Migration
from src.db.migrations.runner import MigrationRunner

__all__ = ["Migration", "MigrationRunner"]
