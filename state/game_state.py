"""
State Pattern: GameState interface for Game Session lifecycle.
Lifecycle: Lobby -> QuestionInProgress -> ShowResults -> (repeat or) FinalPodium.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_session import GameSession


class GameState(ABC):
    """
    Abstract state for the game session lifecycle.
    Concrete states: LobbyState, QuestionState, LeaderboardState, FinishedState.
    """

    @property
    @abstractmethod
    def state_name(self) -> str:
        """Unique name for this state (e.g. for WebSocket events)."""
        pass

    def on_enter(self, session: "GameSession") -> None:
        """
        Called when transitioning into this state.
        Override to broadcast Lobby/Question/Leaderboard/Finished events.
        """
        pass

    def on_leave(self, session: "GameSession") -> None:
        """
        Called when leaving this state for another.
        Override for cleanup if needed.
        """
        pass

    def can_start_question(self, session: "GameSession") -> bool:
        """True if host can trigger 'start question' from this state."""
        return False

    def can_show_leaderboard(self, session: "GameSession") -> bool:
        """True if host can trigger 'show leaderboard' from this state."""
        return False

    def can_go_next(self, session: "GameSession") -> bool:
        """True if host can trigger 'next' (next question or finish)."""
        return False

    def get_next_state(self, session: "GameSession") -> "GameState | None":
        """
        Return the next state when host triggers 'next', or None if no transition.
        Override in concrete states to implement transitions.
        """
        return None
