"""QuizCreatorService: builds Quiz from JSON and persists via QuizRepository (Creator + Factory Method)."""

from typing import Any

from models.quiz import Quiz
from repository.mappers.question_mapper import QuestionMapper
from repository.quiz_repository import QuizRepository


class QuizCreatorService:
    def __init__(self, repository: QuizRepository | None = None) -> None:
        self._repository = repository or QuizRepository()

    async def create_from_dict(self, data: dict[str, Any]) -> str:
        quiz = self._build_quiz(data)
        return await self._repository.insert(quiz)

    def _build_quiz(self, data: dict[str, Any]) -> Quiz:
        title = str(data.get("title", "")).strip() or "Untitled Quiz"
        description = str(data.get("description", "")).strip()
        raw_questions = data.get("questions") or []
        if not raw_questions:
            raise ValueError("Quiz must have at least one question.")
        questions = []
        for qd in raw_questions:
            if isinstance(qd, dict):
                norm = dict(qd)
                if "correct_option" in norm and "correct_index" not in norm:
                    norm["correct_index"] = norm.pop("correct_option", 0)
                if "time_limit" in norm and "time_limit_seconds" not in norm:
                    norm["time_limit_seconds"] = norm.pop("time_limit", 30)
                if "type" in norm and "question_type" not in norm:
                    norm["question_type"] = norm.get("type", "choice")
                questions.append(QuestionMapper.from_dict(norm))
        if not questions:
            raise ValueError("Quiz must have at least one valid question.")
        return Quiz(title=title, description=description, questions=questions)
