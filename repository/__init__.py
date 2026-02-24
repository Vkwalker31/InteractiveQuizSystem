"""
Data access layer: Repository Pattern + Data Mapper.
No ORM; all MongoDB <-> entity mapping is manual.
"""

from repository.mongo_database import MongoDatabase, get_mongo_database
from repository.base_repository import BaseRepository
from repository.quiz_repository import QuizRepository
from repository.mappers import QuestionMapper, QuizMapper

__all__ = [
    "MongoDatabase",
    "get_mongo_database",
    "BaseRepository",
    "QuizRepository",
    "QuestionMapper",
    "QuizMapper",
]
