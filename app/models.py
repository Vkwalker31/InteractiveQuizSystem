from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    text: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    image_url: str | None = None


class QuizCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    questions: list[QuestionCreate] = Field(min_length=1)


class QuizCreated(BaseModel):
    quiz_id: str
    pin: str


class PinValidationResult(BaseModel):
    pin: str
    valid: bool


@dataclass
class SessionState:
    pin: str
    quiz_id: str
    title: str
    total_questions: int
    questions: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    connected_clients: set[str] = field(default_factory=set)
    players: dict[str, str] = field(default_factory=dict)
    state: str = "lobby"
    question_index: int = 0
    answered_clients: set[str] = field(default_factory=set)
    question_correct_indexes: list[int] = field(default_factory=list)
    question_texts: list[str] = field(default_factory=list)
    question_options: list[list[str]] = field(default_factory=list)
    question_image_urls: list[str | None] = field(default_factory=list)
    last_answer_correct: dict[str, bool] = field(default_factory=dict)
    last_score_delta: dict[str, int] = field(default_factory=dict)
    question_started_at: float | None = None
    scores: dict[str, int] = field(default_factory=dict)
    question_timer_task: asyncio.Task[None] | None = None
    leaderboard_timer_task: asyncio.Task[None] | None = None


class RuntimeStore:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def create_session(self, quiz: QuizCreate, quiz_id: str | None = None) -> SessionState:
        quiz_id = quiz_id or uuid4().hex
        pin = self._next_pin()
        session = SessionState(
            pin=pin,
            quiz_id=quiz_id,
            title=quiz.title,
            total_questions=len(quiz.questions),
            questions=[q.model_dump() for q in quiz.questions],
            question_correct_indexes=[q.correct_index for q in quiz.questions],
            question_texts=[q.text for q in quiz.questions],
            question_options=[q.options for q in quiz.questions],
            question_image_urls=[q.image_url for q in quiz.questions],
        )
        self.sessions[pin] = session
        return session

    def has_pin(self, pin: str) -> bool:
        return pin in self.sessions

    def register_client(self, pin: str, client_id: str) -> None:
        self.sessions[pin].connected_clients.add(client_id)

    def unregister_client(self, pin: str, client_id: str) -> None:
        session = self.sessions.get(pin)
        if session:
            session.connected_clients.discard(client_id)

    def _next_pin(self) -> str:
        for _ in range(500):
            pin = str(uuid4().int % 1_000_000).zfill(6)
            if pin not in self.sessions:
                return pin
        raise RuntimeError("Unable to generate unique PIN")


def parse_client_event(payload: dict[str, Any]) -> str:
    return str(payload.get("event_type") or payload.get("type") or "").strip()


def build_state_payload(session: SessionState) -> dict[str, Any]:
    players = [{"client_id": cid, "nickname": nick} for cid, nick in session.players.items()]
    if session.state == "lobby":
        return {
            "event_type": "LOBBY_STATE",
            "pin": session.pin,
            "player_count": len(players),
            "players": players,
        }
    if session.state == "question":
        image_url = None
        question_text = ""
        options: list[str] = []
        if 0 <= session.question_index < len(session.question_image_urls):
            image_url = session.question_image_urls[session.question_index]
        if 0 <= session.question_index < len(session.question_texts):
            question_text = session.question_texts[session.question_index]
        if 0 <= session.question_index < len(session.question_options):
            options = session.question_options[session.question_index]
        return {
            "event_type": "QUESTION_STATE",
            "pin": session.pin,
            "question_id": f"{session.pin}-{session.question_index}",
            "question_index": session.question_index,
            "current_question_index": session.question_index,
            "total_questions": session.total_questions,
            "question_text": question_text,
            "options": options,
            "image_url": image_url,
            "players": players,
        }
    if session.state == "leaderboard":
        ranking = sorted(
            session.players.items(),
            key=lambda item: (-session.scores.get(item[0], 0), item[1].lower()),
        )
        revealed = 0
        if 0 <= session.question_index < len(session.question_correct_indexes):
            revealed = session.question_correct_indexes[session.question_index]
        return {
            "event_type": "LEADERBOARD_STATE",
            "pin": session.pin,
            "question_index": session.question_index,
            "total_questions": session.total_questions,
            "revealed_correct_index": revealed,
            "leaderboard": [
                {"nickname": nick, "score": session.scores.get(cid, 0)}
                for cid, nick in ranking
            ],
            "player_results": session.last_answer_correct,
        }
    return {
        "event_type": "FINISHED_STATE",
        "pin": session.pin,
        "leaderboard": [
            {"nickname": nick, "score": session.scores.get(cid, 0)}
            for cid, nick in sorted(
                session.players.items(),
                key=lambda item: (-session.scores.get(item[0], 0), item[1].lower()),
            )
        ],
        "winners": [
            {"nickname": nick, "score": session.scores.get(cid, 0)}
            for cid, nick in sorted(
                session.players.items(),
                key=lambda item: (-session.scores.get(item[0], 0), item[1].lower()),
            )
        ],
    }