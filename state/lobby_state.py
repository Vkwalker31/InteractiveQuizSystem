"""
Lobby state: players join with PIN; host can start the first question.
"""

from state.game_state import GameState
from state.question_state import QuestionState


class LobbyState(GameState):
    """
    Initial state. Players join; host starts the game -> transition to QuestionState.
    """

    @property
    def state_name(self) -> str:
        return "lobby"

    def can_start_question(self, session) -> bool:
        return True

    def get_next_state(self, session) -> GameState | None:
        """Start first question -> QuestionState."""
        if session.quiz.question_count() == 0:
            return None
        return QuestionState()
