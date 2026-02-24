"""
Multiple-choice question implementation (single correct answer).
"""

from typing import Any

from models.base_question import BaseQuestion


class ChoiceQuestion(BaseQuestion):
    """
    A question with a list of options and one correct answer by index.
    """

    QUESTION_TYPE: str = "choice"

    def __init__(
        self,
        text: str,
        options: list[str],
        correct_index: int,
        time_limit_seconds: int = 30,
        question_id: str | None = None,
    ) -> None:
        super().__init__(
            text=text,
            time_limit_seconds=time_limit_seconds,
            question_id=question_id,
        )
        if not options:
            raise ValueError("ChoiceQuestion must have at least one option.")
        if correct_index < 0 or correct_index >= len(options):
            raise ValueError(
                f"correct_index {correct_index} must be in range [0, {len(options)})"
            )
        self._options: list[str] = list(options)
        self._correct_index: int = correct_index

    @property
    def options(self) -> list[str]:
        """Ordered list of answer options."""
        return self._options

    @property
    def correct_index(self) -> int:
        """Index of the correct option (0-based)."""
        return self._correct_index

    def validate_answer(self, answer: Any) -> bool:
        """Answer is correct if it equals the correct index (int)."""
        if not isinstance(answer, int):
            return False
        return answer == self._correct_index

    def to_mappable_dict(self) -> dict[str, Any]:
        base = {
            "question_type": self.QUESTION_TYPE,
            "text": self._text,
            "time_limit_seconds": self._time_limit_seconds,
            "options": self._options,
            "correct_index": self._correct_index,
        }
        if self._question_id is not None:
            base["_id"] = self._question_id
        return base

    def __repr__(self) -> str:
        return (
            f"ChoiceQuestion(id={self._question_id!r}, options_count={len(self._options)})"
        )
