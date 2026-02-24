"""
Data Mapper: raw MongoDB document <-> Quiz entity.
Uses QuestionMapper for embedded or referenced questions.
"""

from datetime import datetime
from typing import Any

from bson import ObjectId

from models.quiz import Quiz
from repository.mappers.question_mapper import QuestionMapper


class QuizMapper:
    """
    Maps BSON/dict from MongoDB to Quiz domain entity (and back for insert/update).
    Questions are expected as a list of dicts under "questions" key.
    """

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Quiz:
        """
        Build a Quiz entity from a MongoDB document.
        Expects data["questions"] to be a list of question dicts (each with question_type).
        """
        if not isinstance(data, dict):
            raise ValueError("Quiz data must be a dict.")

        quiz_id = cls._extract_id(data)
        title = data.get("title", "")
        description = data.get("description", "")
        created_at = cls._extract_datetime(data.get("created_at"))
        raw_questions = data.get("questions") or []

        questions = []
        for i, q_data in enumerate(raw_questions):
            if isinstance(q_data, dict):
                question = QuestionMapper.from_dict(q_data)
                questions.append(question)
            # Skip malformed entries

        if not questions:
            raise ValueError("Quiz document must have at least one valid question.")

        quiz = Quiz(
            title=title,
            questions=questions,
            quiz_id=quiz_id,
            description=description,
            created_at=created_at,
        )
        return quiz

    @staticmethod
    def _extract_id(data: dict[str, Any]) -> str | None:
        raw = data.get("_id")
        if raw is None:
            return None
        return str(raw)

    @staticmethod
    def _extract_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def to_dict(quiz: Quiz) -> dict[str, Any]:
        """
        Serialize a Quiz entity to a dict suitable for MongoDB insert/update.
        Does not include _id (let MongoDB generate on insert, or set explicitly).
        """
        doc: dict[str, Any] = {
            "title": quiz.title,
            "description": quiz.description,
            "questions": [q.to_mappable_dict() for q in quiz.questions],
            "created_at": quiz.created_at,
        }
        if quiz.quiz_id is not None:
            try:
                doc["_id"] = ObjectId(quiz.quiz_id)
            except (TypeError, ValueError):
                doc["_id"] = quiz.quiz_id
        return doc
