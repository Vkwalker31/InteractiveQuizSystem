"""
Abstract base class for repositories (Repository Pattern).
Defines the contract for data access; concrete repos abstract MongoDB operations.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from repository.mongo_database import MongoDatabase

T_entity = TypeVar("T_entity")
T_id = TypeVar("T_id", str, int)


class BaseRepository(ABC, Generic[T_entity, T_id]):
    """
    Abstract base repository: provides access to MongoDB collection
    and delegates entity mapping to subclasses / mappers.
    """

    def __init__(self, database: MongoDatabase | None = None) -> None:
        """
        Args:
            database: MongoDatabase singleton. If None, uses get_instance().
        """
        self._db: MongoDatabase = database or MongoDatabase.get_instance()

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """MongoDB collection name (e.g. 'quizzes', 'questions')."""
        pass

    def get_collection(self) -> AsyncIOMotorCollection:
        """Return the motor collection for this repository."""
        return self._db.get_database()[self.collection_name]

    @abstractmethod
    async def find_by_id(self, id: T_id) -> T_entity | None:
        """Load a single entity by its identifier. Returns None if not found."""
        pass

    @abstractmethod
    async def insert(self, entity: T_entity) -> T_id:
        """Persist a new entity and return its assigned id."""
        pass
