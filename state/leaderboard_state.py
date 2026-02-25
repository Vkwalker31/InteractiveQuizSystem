"""
Leaderboard state: show results after a question; host can go to next question or finish.
"""

from typing import TYPE_CHECKING

from state.game_state import GameState

if TYPE_CHECKING:
    from models.game_session import GameSession


class LeaderboardState(GameState):
    """
    Showing scores after a question. Host triggers 'next':
    - If there is a next question -> QuestionState (and advance index).
    - Else -> FinishedState.
    """

    @property
    def state_name(self) -> str:
        return "leaderboard"

    def can_go_next(self, session: "GameSession") -> bool:
        return True

    def get_next_state(self, session: "GameSession") -> GameState | None:
        if session.has_next_question():
            session.advance_to_next_question()
            from state.question_state import QuestionState
            return QuestionState()
        from state.finished_state import FinishedState
        return FinishedState()
