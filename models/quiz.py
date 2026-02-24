"""
Quiz entity: aggregates questions and metadata.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from models.base_question import BaseQuestion

if TYPE_CHECKING:
    pass


class Quiz:
    """
    Domain entity representing a full quiz (title + ordered list of questions).
    Persisted in MongoDB; mapping done via QuizRepository / Data Mapper.
    """

    def __init__(
        self,
        title: str,
        questions: list[BaseQuestion],
        quiz_id: str | None = None,
        description: str = "",
        created_at: datetime | None = None,
    ) -> None:
        """
        Args:
            title: Display title of the quiz.
            questions: Ordered list of question entities (ChoiceQuestion / TrueFalseQuestion).
            quiz_id: Optional persistent ID from database.
            description: Optional description.
            created_at: Optional creation timestamp.
        """
        if not questions:
            raise ValueError("Quiz must have at least one question.")
        self._quiz_id: str | None = quiz_id
        self._title: str = title
        self._description: str = description
        self._questions: list[BaseQuestion] = list(questions)
        self._created_at: datetime = created_at or datetime.utcnow()

    @property
    def quiz_id(self) -> str | None:
        """Unique identifier for persistence."""
        return self._quiz_id

    @quiz_id.setter
    def quiz_id(self, value: str | None) -> None:
        self._quiz_id = value

    @property
    def title(self) -> str:
        """Quiz title."""
        return self._title

    @property
    def description(self) -> str:
        """Optional description."""
        return self._description

    @property
    def questions(self) -> list[BaseQuestion]:
        """Ordered list of questions (read-only list reference)."""
        return self._questions

    @property
    def created_at(self) -> datetime:
        """Creation timestamp."""
        return self._created_at

    def question_count(self) -> int:
        """Number of questions."""
        return len(self._questions)

    def get_question_at(self, index: int) -> BaseQuestion | None:
        """Safe getter for question by index; returns None if out of range."""
        if 0 <= index < len(self._questions):
            return self._questions[index]
        return None

    def __repr__(self) -> str:
        return f"Quiz(id={self._quiz_id!r}, title={self._title!r}, questions={len(self._questions)})"
