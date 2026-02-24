"""
Data Mapper + Factory Method: raw MongoDB document -> BaseQuestion.
Instantiates ChoiceQuestion or TrueFalseQuestion based on question_type.
"""

from typing import Any

from models.base_question import BaseQuestion
from models.choice_question import ChoiceQuestion
from models.true_false_question import TrueFalseQuestion


class QuestionMapper:
    """
    Maps BSON/dict from MongoDB to domain BaseQuestion subclasses.
    Implements Factory Method: from_dict dispatches by question_type.
    """

    TYPE_CHOICE: str = "choice"
    TYPE_TRUE_FALSE: str = "true_false"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseQuestion:
        """
        Build a domain question entity from a MongoDB document (or dict).
        Uses question_type to choose ChoiceQuestion vs TrueFalseQuestion.

        Args:
            data: Dict with keys: question_type, text, time_limit_seconds,
                  and type-specific fields (options/correct_index or correct_answer).
        Returns:
            ChoiceQuestion or TrueFalseQuestion instance.
        """
        if not isinstance(data, dict):
            raise ValueError("Question data must be a dict.")

        q_type = data.get("question_type") or data.get("type")
        text = data.get("text", "")
        time_limit = int(data.get("time_limit_seconds", 30))
        question_id = cls._extract_id(data)

        if q_type == cls.TYPE_CHOICE:
            return cls._map_choice(data, text, time_limit, question_id)
        if q_type == cls.TYPE_TRUE_FALSE:
            return cls._map_true_false(data, text, time_limit, question_id)

        raise ValueError(f"Unknown question_type: {q_type!r}")

    @staticmethod
    def _extract_id(data: dict[str, Any]) -> str | None:
        """Convert MongoDB _id (ObjectId or str) to str for domain."""
        raw = data.get("_id")
        if raw is None:
            return None
        return str(raw)

    @classmethod
    def _map_choice(
        cls,
        data: dict[str, Any],
        text: str,
        time_limit: int,
        question_id: str | None,
    ) -> ChoiceQuestion:
        options = data.get("options") or []
        if isinstance(options, (list, tuple)):
            options = list(options)
        else:
            options = []
        correct_index = int(data.get("correct_index", 0))
        return ChoiceQuestion(
            text=text,
            options=options,
            correct_index=correct_index,
            time_limit_seconds=time_limit,
            question_id=question_id,
        )

    @classmethod
    def _map_true_false(
        cls,
        data: dict[str, Any],
        text: str,
        time_limit: int,
        question_id: str | None,
    ) -> TrueFalseQuestion:
        raw = data.get("correct_answer")
        if isinstance(raw, bool):
            correct_answer = raw
        elif raw in ("true", "True", "1", 1):
            correct_answer = True
        elif raw in ("false", "False", "0", 0):
            correct_answer = False
        else:
            correct_answer = bool(raw)
        return TrueFalseQuestion(
            text=text,
            correct_answer=correct_answer,
            time_limit_seconds=time_limit,
            question_id=question_id,
        )
