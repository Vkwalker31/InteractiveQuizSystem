from __future__ import annotations

import os
from typing import Protocol
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.models import QuizCreate


class QuizDefinitionRepository(Protocol):
    async def save_quiz(self, quiz: QuizCreate) -> str:
        ...

    async def update_quiz(self, quiz_id: str, quiz: QuizCreate) -> bool:
        ...

    async def delete_quiz(self, quiz_id: str) -> bool:
        ...

    async def get_quiz(self, quiz_id: str) -> dict | None:
        ...

    async def ping(self) -> bool:
        ...

    async def list_quizzes(self) -> list[dict]:
        ...

    async def save_session_history(self, record: dict) -> None:
        ...


class InMemoryQuizRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._session_history: list[dict] = []

    async def save_quiz(self, quiz: QuizCreate) -> str:
        quiz_id = uuid4().hex
        self._items[quiz_id] = {
            "_id": quiz_id,
            "title": quiz.title,
            "description": quiz.description,
            "questions": [q.model_dump() for q in quiz.questions],
        }
        return quiz_id

    async def get_quiz(self, quiz_id: str) -> dict | None:
        return self._items.get(quiz_id)

    async def update_quiz(self, quiz_id: str, quiz: QuizCreate) -> bool:
        if quiz_id not in self._items:
            return False
        self._items[quiz_id] = {
            "_id": quiz_id,
            "title": quiz.title,
            "description": quiz.description,
            "questions": [q.model_dump() for q in quiz.questions],
        }
        return True

    async def delete_quiz(self, quiz_id: str) -> bool:
        if quiz_id in self._items:
            self._items.pop(quiz_id, None)
            return True
        return False

    async def ping(self) -> bool:
        return True

    async def list_quizzes(self) -> list[dict]:
        return [
            {
                "quiz_id": quiz_id,
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "question_count": len(item.get("questions", [])),
            }
            for quiz_id, item in self._items.items()
        ]

    async def save_session_history(self, record: dict) -> None:
        self._session_history.append(dict(record))


class MongoQuizRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._db = database
        self._collection: AsyncIOMotorCollection = database["quizzes"]
        self._history: AsyncIOMotorCollection = database["session_history"]

    @classmethod
    def from_env(cls) -> "MongoQuizRepository":
        uri = os.environ.get("MONGODB_URI") or os.environ.get(
            "MONGO_URI", "mongodb://127.0.0.1:27017"
        )
        db_name = os.environ.get("MONGODB_DATABASE", "quiz_system")
        client = AsyncIOMotorClient(uri)
        return cls(client[db_name])

    async def save_quiz(self, quiz: QuizCreate) -> str:
        document = {
            "title": quiz.title,
            "description": quiz.description,
            "questions": [q.model_dump() for q in quiz.questions],
        }
        result = await self._collection.insert_one(document)
        return str(result.inserted_id)

    async def update_quiz(self, quiz_id: str, quiz: QuizCreate) -> bool:
        document = {
            "title": quiz.title,
            "description": quiz.description,
            "questions": [q.model_dump() for q in quiz.questions],
        }
        try:
            oid = ObjectId(quiz_id)
            result = await self._collection.update_one({"_id": oid}, {"$set": document})
        except Exception:
            result = await self._collection.update_one({"_id": quiz_id}, {"$set": document})
        return bool(result.matched_count)

    async def delete_quiz(self, quiz_id: str) -> bool:
        try:
            oid = ObjectId(quiz_id)
            result = await self._collection.delete_one({"_id": oid})
        except Exception:
            result = await self._collection.delete_one({"_id": quiz_id})
        return bool(result.deleted_count)

    async def get_quiz(self, quiz_id: str) -> dict | None:
        try:
            oid = ObjectId(quiz_id)
            doc = await self._collection.find_one({"_id": oid})
        except Exception:
            doc = await self._collection.find_one({"_id": quiz_id})
        if not doc:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def ping(self) -> bool:
        try:
            await self._db.command("ping")
            return True
        except Exception:
            return False

    async def list_quizzes(self) -> list[dict]:
        rows: list[dict] = []
        cursor = self._collection.find(
            {},
            {"_id": 1, "title": 1, "description": 1, "questions": 1},
        )
        async for doc in cursor:
            raw_id = doc.get("_id")
            quiz_id = str(raw_id) if raw_id is not None else ""
            qs = doc.get("questions")
            rows.append(
                {
                    "quiz_id": quiz_id,
                    "title": doc.get("title") or "",
                    "description": doc.get("description") or "",
                    "question_count": len(qs) if isinstance(qs, list) else 0,
                }
            )
        return rows

    async def save_session_history(self, record: dict) -> None:
        await self._history.insert_one(dict(record))

