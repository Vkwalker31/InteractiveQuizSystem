"""
Finished state: game over (Final Podium). No further transitions.
"""

from typing import TYPE_CHECKING

from state.game_state import GameState

if TYPE_CHECKING:
    from models.game_session import GameSession


class FinishedState(GameState):
    """
    Final state. Game over; leaderboard/podium can be shown.
    No transitions.
    """

    @property
    def state_name(self) -> str:
        return "finished"

    def can_go_next(self, session: "GameSession") -> bool:
        return False

    def get_next_state(self, session: "GameSession") -> GameState | None:
        return None
