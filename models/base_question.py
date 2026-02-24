"""
Abstract base class for all question types in the Quiz System.
Implements the common interface for questions (Factory Method pattern target).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseQuestion(ABC):
    """
    Abstract base class defining the contract for all question types.
    Subclasses must implement type-specific validation and serialization.
    """

    QUESTION_TYPE: str = "base"  # Override in subclasses for discriminator

    def __init__(
        self,
        text: str,
        time_limit_seconds: int = 30,
        question_id: str | None = None,
    ) -> None:
        """
        Initialize base question attributes.

        Args:
            text: The question text displayed to players.
            time_limit_seconds: Time allowed to answer (default 30).
            question_id: Optional persistent ID from database.
        """
        self._question_id: str | None = question_id
        self._text: str = text
        self._time_limit_seconds: int = time_limit_seconds

    @property
    def question_id(self) -> str | None:
        """Unique identifier for persistence (Data Mapper / Repository)."""
        return self._question_id

    @question_id.setter
    def question_id(self, value: str | None) -> None:
        self._question_id = value

    @property
    def text(self) -> str:
        """The question text."""
        return self._text

    @property
    def time_limit_seconds(self) -> int:
        """Time limit for answering in seconds."""
        return self._time_limit_seconds

    @property
    def question_type(self) -> str:
        """Discriminator for Factory Method when reconstructing from DB."""
        return self.QUESTION_TYPE

    @abstractmethod
    def validate_answer(self, answer: Any) -> bool:
        """
        Check if the given answer is correct.

        Args:
            answer: Player's answer (type depends on question subtype).

        Returns:
            True if answer is correct, False otherwise.
        """
        pass

    @abstractmethod
    def to_mappable_dict(self) -> dict[str, Any]:
        """
        Serialize to a dict suitable for MongoDB (Data Mapper reverse direction).
        Subclasses extend with their specific fields.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._question_id!r}, text={self._text[:50]!r}...)"
