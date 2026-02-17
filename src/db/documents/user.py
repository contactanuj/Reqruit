"""
User document model — authentication and account management.

This is the simplest document in the system. A User represents a registered
account with login credentials. All other collections reference the user's
ObjectId to associate data with a specific person.

Design decisions
----------------
Why email as the unique identifier (not username):
    Email is universally unique, already verified by users, and serves as
    a natural login credential. Username-based systems require an additional
    email field for password resets and notifications anyway.

Why store hashed_password in the same collection (not a separate auth collection):
    For a single-user learning project, the simpler approach is fine.
    In multi-service architectures, separating auth data into its own
    service/collection prevents accidental exposure during user queries.
    We can refactor later if needed.

Why is_active instead of deleting users:
    Soft-delete pattern. Deactivating preserves the user's history
    (applications, documents, STAR stories) for potential reactivation.
    Hard deletion would orphan all referenced documents and require
    cascade-delete logic across 11 other collections.
"""

from beanie import Indexed

from src.db.base_document import TimestampedDocument


class User(TimestampedDocument):
    """
    Registered user account.

    Fields:
        email: Unique login identifier. Indexed for fast lookup during auth.
        hashed_password: bcrypt hash. Never stored or transmitted in plaintext.
        is_active: False = soft-deleted. Inactive users cannot log in.
    """

    email: Indexed(str, unique=True)
    hashed_password: str
    is_active: bool = True

    class Settings:
        name = "users"
