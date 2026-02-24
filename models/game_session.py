"""
GameSession entity: the heart of a live game (PIN, quiz, players, state).
State transitions are delegated to the State Pattern (state layer).
"""

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from models.base_question import BaseQuestion
from models.player import Player
from models.quiz import Quiz

if TYPE_CHECKING:
    from state.game_state import GameState


class GameSession:
    """
    Represents a single live quiz session.
    Holds PIN, the quiz being played, connected players, and current state.
    State object (GameState) controls lifecycle: Lobby -> Question -> Leaderboard -> Finished.
    """

    def __init__(
        self,
        pin: str,
        quiz: Quiz,
        session_id: str | None = None,
        created_at: datetime | None = None,
        initial_state: "GameState | None" = None,
    ) -> None:
        """
        Args:
            pin: Short PIN for players to join (e.g. 6-digit).
            quiz: The Quiz entity to play.
            session_id: Optional persistent ID (if we store sessions in DB later).
            created_at: When the session was created.
            initial_state: State to start in (default: LobbyState).
        """
        self._session_id: str | None = session_id
        self._pin: str = pin
        self._quiz: Quiz = quiz
        self._players: dict[str, Player] = {}  # connection_id -> Player
        self._current_question_index: int = 0
        self._created_at: datetime = created_at or datetime.utcnow()
        self._state: "GameState | None" = initial_state
        if self._state is None:
            from state.lobby_state import LobbyState
            self._state = LobbyState()
        # Optional callback invoked after state transition (Observer: triggers ConnectionManager broadcast).
        self._broadcast_callback: Callable[[], None] | None = None
        # Connection IDs that already answered the current question (no double-scoring).
        self._current_question_answered: set[str] = set()

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def pin(self) -> str:
        """PIN displayed to players to join."""
        return self._pin

    @property
    def quiz(self) -> Quiz:
        """The quiz being played."""
        return self._quiz

    @property
    def players(self) -> dict[str, Player]:
        """Map of connection_id -> Player."""
        return self._players

    @property
    def current_question_index(self) -> int:
        """Index of the current question (0-based)."""
        return self._current_question_index

    @current_question_index.setter
    def current_question_index(self, value: int) -> None:
        self._current_question_index = value

    @property
    def state(self) -> "GameState | None":
        """Current state in the State Pattern."""
        return self._state

    @state.setter
    def state(self, value: "GameState | None") -> None:
        self._state = value

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def add_player(self, player: Player) -> None:
        """Register a player in this session (connection_id must be unique)."""
        self._players[player.connection_id] = player

    def remove_player(self, connection_id: str) -> Player | None:
        """Remove player by connection_id; returns the removed Player or None."""
        return self._players.pop(connection_id, None)

    def get_player(self, connection_id: str) -> Player | None:
        """Get player by connection_id."""
        return self._players.get(connection_id)

    def set_broadcast_callback(self, callback: Callable[[], None] | None) -> None:
        """Set callback invoked after state transition (used to broadcast via ConnectionManager)."""
        self._broadcast_callback = callback

    def clear_current_question_answers(self) -> None:
        """Clear the set of players who answered the current question (call when entering QuestionState)."""
        self._current_question_answered.clear()

    def has_answered_current_question(self, connection_id: str) -> bool:
        """True if this connection already submitted an answer for the current question."""
        return connection_id in self._current_question_answered

    def record_answer(self, connection_id: str) -> bool:
        """Record that this connection answered the current question. Returns True if first time."""
        if connection_id in self._current_question_answered:
            return False
        self._current_question_answered.add(connection_id)
        return True

    def get_current_question(self) -> BaseQuestion | None:
        """Returns the BaseQuestion at current_question_index, or None."""
        return self._quiz.get_question_at(self._current_question_index)

    def has_next_question(self) -> bool:
        """True if there is a next question after the current index."""
        return self._current_question_index + 1 < self._quiz.question_count()

    def advance_to_next_question(self) -> bool:
        """
        Move to next question. Returns True if advanced, False if no more questions.
        """
        if not self.has_next_question():
            return False
        self._current_question_index += 1
        return True

    def transition_to(self, new_state: "GameState") -> None:
        """
        Transition to a new state (State Pattern).
        Calls on_leave on current state, sets new state, calls on_enter,
        then invokes broadcast callback so ConnectionManager notifies all clients (Observer).
        """
        if self._state is not None:
            self._state.on_leave(self)
        self._state = new_state
        if self._state is not None:
            self._state.on_enter(self)
        if self._broadcast_callback is not None:
            self._broadcast_callback()

    def trigger_next(self) -> bool:
        """
        Host triggers 'next' (start question, show leaderboard, or finish).
        Uses current state's get_next_state() and transition_to().
        Returns True if state changed, False otherwise.
        """
        if self._state is None or not self._state.can_go_next(self):
            return False
        next_state = self._state.get_next_state(self)
        if next_state is None:
            return False
        self.transition_to(next_state)
        return True

    def trigger_start_question(self) -> bool:
        """
        Host triggers 'start question' from lobby.
        Returns True if transitioned to QuestionState.
        """
        if self._state is None or not self._state.can_start_question(self):
            return False
        next_state = self._state.get_next_state(self)
        if next_state is None:
            return False
        self.transition_to(next_state)
        return True

    def __repr__(self) -> str:
        return (
            f"GameSession(pin={self._pin!r}, players={len(self._players)}, "
            f"question_index={self._current_question_index})"
        )
