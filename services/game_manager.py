"""
GameManager: Singleton (Creational Pattern) that holds active game sessions keyed by 6-digit PIN.
Creates sessions, looks them up, and removes them when the game ends.
Used by FastAPI routes and WebSocket endpoint.
"""

import random
from typing import TYPE_CHECKING

from models.game_session import GameSession
from models.quiz import Quiz

if TYPE_CHECKING:
    pass


class GameManager:

    _instance: "GameManager | None" = None

    def __new__(cls) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_sessions"):
            return
        self._sessions: dict[str, GameSession] = {}

    def create_session(self, quiz: Quiz) -> tuple[GameSession, str]:
        pin = self._generate_pin()
        session = GameSession(pin=pin, quiz=quiz)
        self._sessions[pin] = session
        return session, pin

    def get_session(self, pin: str) -> GameSession | None:
        return self._sessions.get(pin)

    def remove_session(self, pin: str) -> GameSession | None:
        return self._sessions.pop(pin, None)

    def _generate_pin(self) -> str:
        for _ in range(100):
            pin = "".join(str(random.randint(0, 9)) for _ in range(6))
            if pin not in self._sessions:
                return pin
        raise RuntimeError("Could not generate unique 6-digit PIN")

    @classmethod
    def get_instance(cls) -> "GameManager":
        return cls()
