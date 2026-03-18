"""
User repository — data access methods for user authentication and management.

This is the first concrete repository in the project. It extends
BaseRepository[User] with auth-specific queries and serves as the pattern
for all future repositories (ProfileRepository, JobRepository, etc.).

Design decisions
----------------
Why a concrete repository (not just BaseRepository[User] directly):
    Auth queries are specific to the User model — get_by_email, email_exists,
    create_user. These belong in a dedicated repository, not in a generic
    base class. The base class handles universal CRUD; the concrete class
    handles domain-specific queries.

    This also keeps the service layer clean:
        # Service code
        user = await self.user_repo.get_by_email(email)
    vs.
        # Without a concrete repo — service knows about MongoDB queries
        user = await User.find_one({"email": email})

Why create_user() constructs the User object:
    The repository owns the creation logic — it knows what fields are
    required, what defaults to apply, and how to handle the insert. The
    service just passes the validated inputs. This prevents services
    from constructing User objects with missing or invalid fields.

Usage
-----
    from src.repositories.user_repository import UserRepository

    repo = UserRepository()
    user = await repo.get_by_email("user@example.com")
    exists = await repo.email_exists("user@example.com")
    new_user = await repo.create_user("new@example.com", hashed_password)
"""

from src.db.documents.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User-specific data access methods extending the generic BaseRepository."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, email: str) -> User | None:
        """
        Find a user by their email address.

        Used during login to verify credentials. Returns None if no user
        with this email exists (does not raise — the auth service decides
        whether to return an error or allow registration).
        """
        return await self.find_one({"email": email})

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email address is already registered.

        Used during registration to prevent duplicate accounts. More
        efficient than get_by_email() when you only need existence, not
        the full document — though at our scale the difference is negligible.
        """
        user = await self.find_one({"email": email})
        return user is not None

    async def create_user(self, email: str, hashed_password: str) -> User:
        """
        Create a new user account.

        The password must be pre-hashed by the caller (auth service).
        This repository never handles plaintext passwords.

        Args:
            email: Unique email address for the account.
            hashed_password: bcrypt hash of the user's password.

        Returns:
            The created User document with generated _id and timestamps.

        Raises:
            DatabaseError: If insertion fails (e.g., duplicate email
                despite the unique index — a race condition).
        """
        user = User(email=email, hashed_password=hashed_password)
        return await self.create(user)
