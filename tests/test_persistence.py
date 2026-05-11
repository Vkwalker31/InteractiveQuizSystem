from __future__ import annotations

import asyncio
from types import SimpleNamespace

from bson import ObjectId

from app.database import InMemoryQuizRepository, MongoQuizRepository
from app.models import QuizCreate


def _sample_quiz() -> QuizCreate:
    return QuizCreate(
        title="Persistent Quiz",
        description="Storage test",
        questions=[
            {"text": "2+2", "options": ["1", "2", "3", "4"], "correct_index": 3}
        ],
    )


def test_inmemory_repository_saves_and_loads_quiz_definition() -> None:
    repo = InMemoryQuizRepository()
    quiz = _sample_quiz()
    quiz_id = asyncio.run(repo.save_quiz(quiz))
    loaded = asyncio.run(repo.get_quiz(quiz_id))

    assert loaded is not None
    assert loaded["_id"] == quiz_id
    assert loaded["title"] == "Persistent Quiz"
    assert loaded["questions"][0]["correct_index"] == 3


def test_mongo_repository_saves_and_loads_quiz_definition_with_fake_collection() -> None:
    class FakeCollection:
        def __init__(self) -> None:
            self.docs: dict[str, dict] = {}

        async def insert_one(self, document: dict):
            oid = ObjectId()
            saved = {**document, "_id": oid}
            self.docs[str(oid)] = saved
            return SimpleNamespace(inserted_id=oid)

        async def find_one(self, query: dict):
            if "_id" in query:
                key = str(query["_id"])
                return self.docs.get(key)
            return None

    fake = FakeCollection()
    repo = MongoQuizRepository.__new__(MongoQuizRepository)
    repo._collection = fake
    repo._db = None

    quiz_id = asyncio.run(repo.save_quiz(_sample_quiz()))
    loaded = asyncio.run(repo.get_quiz(quiz_id))

    assert loaded is not None
    assert loaded["_id"] == quiz_id
    assert loaded["title"] == "Persistent Quiz"
    assert loaded["questions"][0]["text"] == "2+2"

