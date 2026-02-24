"""
Singleton for MongoDB connection pool (motor async driver).
Ensures a single shared connection across the application.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoDatabase:
    """
    Singleton providing asynchronous MongoDB connection and database access.
    Use get_instance() to obtain the single instance; call connect() at startup.
    """

    _instance: "MongoDatabase | None" = None
    _client: AsyncIOMotorClient | None = None
    _database_name: str = "quiz_system"
    _initialized: bool = False

    def __new__(cls) -> "MongoDatabase":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(
        self,
        uri: str = "mongodb://localhost:27017",
        database_name: str = "quiz_system",
        **kwargs: Any,
    ) -> None:
        """
        Initialize the motor client and store database name.
        Idempotent: safe to call multiple times; reuses existing client if uri matches.
        """
        if self._client is None:
            self._client = AsyncIOMotorClient(uri, **kwargs)
            self._database_name = database_name
            self._initialized = True

    def close(self) -> None:
        """Close the motor client. No-op if not connected."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._initialized = False

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Return the motor database instance for the configured database name.
        Raises RuntimeError if connect() was not called first.
        """
        if self._client is None:
            raise RuntimeError(
                "MongoDatabase not connected. Call connect(uri, database_name) first."
            )
        return self._client[self._database_name]

    @property
    def is_initialized(self) -> bool:
        """True if connect() has been called and client is set."""
        return self._initialized and self._client is not None

    @classmethod
    def get_instance(cls) -> "MongoDatabase":
        """Return the singleton instance."""
        return cls()


# Convenience alias for dependency injection
def get_mongo_database() -> MongoDatabase:
    """Return the MongoDatabase singleton (for FastAPI Depends etc.)."""
    return MongoDatabase.get_instance()
