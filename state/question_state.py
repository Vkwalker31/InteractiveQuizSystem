"""
Question state: a question is in progress; host can show leaderboard when time is up.
"""

from typing import TYPE_CHECKING

from state.game_state import GameState

if TYPE_CHECKING:
    from models.game_session import GameSession


class QuestionState(GameState):
    """
    A question is being displayed; players submit answers.
    Host triggers 'next' -> show leaderboard (LeaderboardState),
    or if no more questions -> FinishedState.
    """

    @property
    def state_name(self) -> str:
        return "question"

    def on_enter(self, session: "GameSession") -> None:
        """Clear answered set so players can submit for this question."""
        session.clear_current_question_answers()

    def can_show_leaderboard(self, session: "GameSession") -> bool:
        return True

    def can_go_next(self, session: "GameSession") -> bool:
        return True

    def get_next_state(self, session: "GameSession") -> GameState | None:
        """
        After showing results: go to LeaderboardState.
        (LeaderboardState.get_next_state will decide Question vs Finished.)
        """
        from state.leaderboard_state import LeaderboardState
        return LeaderboardState()
