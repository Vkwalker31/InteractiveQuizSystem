"""
True/False question implementation.
"""

from typing import Any

from models.base_question import BaseQuestion


class TrueFalseQuestion(BaseQuestion):
    """
    A question with exactly two outcomes: True or False.
    """

    QUESTION_TYPE: str = "true_false"

    def __init__(
        self,
        text: str,
        correct_answer: bool,
        time_limit_seconds: int = 30,
        question_id: str | None = None,
    ) -> None:
        super().__init__(
            text=text,
            time_limit_seconds=time_limit_seconds,
            question_id=question_id,
        )
        self._correct_answer: bool = correct_answer

    @property
    def correct_answer(self) -> bool:
        """The correct boolean answer."""
        return self._correct_answer

    def validate_answer(self, answer: Any) -> bool:
        """Answer is correct if it equals the correct boolean."""
        if not isinstance(answer, bool):
            # Allow 0/1 or "true"/"false" from JSON if needed; keep strict here
            return False
        return answer == self._correct_answer

    def to_mappable_dict(self) -> dict[str, Any]:
        base = {
            "question_type": self.QUESTION_TYPE,
            "text": self._text,
            "time_limit_seconds": self._time_limit_seconds,
            "correct_answer": self._correct_answer,
        }
        if self._question_id is not None:
            base["_id"] = self._question_id
        return base

    def __repr__(self) -> str:
        return (
            f"TrueFalseQuestion(id={self._question_id!r}, "
            f"correct_answer={self._correct_answer})"
        )
