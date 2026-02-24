"""
Quiz repository: abstracts MongoDB access for Quiz entities.
Uses QuizMapper for manual dict <-> Quiz mapping (no ORM).
"""

from bson import ObjectId

from models.quiz import Quiz
from repository.base_repository import BaseRepository
from repository.mappers.quiz_mapper import QuizMapper


class QuizRepository(BaseRepository[Quiz, str]):
    """Repository for Quiz aggregate (collection: quizzes)."""

    @property
    def collection_name(self) -> str:
        return "quizzes"

    async def find_by_id(self, id: str) -> Quiz | None:
        """
        Load a quiz by ID (string or 24-char hex for ObjectId).
        Returns None if not found or invalid id.
        """
        coll = self.get_collection()
        try:
            obj_id = ObjectId(id)
            doc = await coll.find_one({"_id": obj_id})
        except Exception:
            doc = await coll.find_one({"_id": id})
        if doc is None:
            return None
        doc = self._normalize_doc_id(doc)
        return QuizMapper.from_dict(doc)

    @staticmethod
    def _normalize_doc_id(doc: dict) -> dict:
        """Convert _id to string for mapper (ObjectId -> str)."""
        if doc and "_id" in doc and hasattr(doc["_id"], "hex"):
            doc = {**doc, "_id": str(doc["_id"])}
        return doc

    async def find_all(self) -> list[Quiz]:
        """Load all quizzes (order by created_at descending)."""
        coll = self.get_collection()
        cursor = coll.find().sort("created_at", -1)
        result: list[Quiz] = []
        async for doc in cursor:
            doc = QuizRepository._normalize_doc_id(doc)
            result.append(QuizMapper.from_dict(doc))
        return result

    async def insert(self, entity: Quiz) -> str:
        """
        Persist a new quiz. Sets entity.quiz_id to the generated _id after insert.
        Returns the new quiz id (string).
        """
        coll = self.get_collection()
        doc = QuizMapper.to_dict(entity)
        # Let MongoDB generate _id for new quizzes
        if entity.quiz_id is None:
            doc.pop("_id", None)
        result = await coll.insert_one(doc)
        inserted_id = result.inserted_id
        entity.quiz_id = str(inserted_id)
        return str(inserted_id)

    async def update(self, entity: Quiz) -> bool:
        """
        Update an existing quiz by _id. Returns True if a document was modified.
        """
        if entity.quiz_id is None:
            raise ValueError("Cannot update quiz without quiz_id.")
        coll = self.get_collection()
        doc = QuizMapper.to_dict(entity)
        obj_id = ObjectId(entity.quiz_id)
        del doc["_id"]
        result = await coll.update_one({"_id": obj_id}, {"$set": doc})
        return result.modified_count > 0
