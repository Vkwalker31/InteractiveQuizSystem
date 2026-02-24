"""
Player entity: represents a participant in a game session.
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # No circular imports needed for Player


class Player:
    """
    Domain entity for a player in a live quiz session.
    Tied to a WebSocket connection via connection_id.
    """

    def __init__(
        self,
        connection_id: str,
        nickname: str,
        score: int = 0,
        joined_at: datetime | None = None,
    ) -> None:
        """
        Args:
            connection_id: Unique ID of the WebSocket connection (used by ConnectionManager).
            nickname: Display name chosen by the player.
            score: Current score in this session (updated by scoring strategy).
            joined_at: When the player joined the lobby (default: now).
        """
        self._connection_id: str = connection_id
        self._nickname: str = nickname
        self._score: int = score
        self._joined_at: datetime = joined_at or datetime.utcnow()

    @property
    def connection_id(self) -> str:
        """WebSocket connection identifier."""
        return self._connection_id

    @property
    def nickname(self) -> str:
        """Player's display name."""
        return self._nickname

    @property
    def score(self) -> int:
        """Current score in the game session."""
        return self._score

    @score.setter
    def score(self, value: int) -> None:
        if value < 0:
            raise ValueError("Score cannot be negative.")
        self._score = value

    def add_score(self, points: int) -> None:
        """Add points to current score (used by ScoringStrategy)."""
        self._score += points

    @property
    def joined_at(self) -> datetime:
        """Timestamp when the player joined the lobby."""
        return self._joined_at

    def to_mappable_dict(self) -> dict:
        """For serialization / leaderboard DTOs (no persistence of Player in MongoDB)."""
        return {
            "connection_id": self._connection_id,
            "nickname": self._nickname,
            "score": self._score,
            "joined_at": self._joined_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"Player(connection_id={self._connection_id!r}, nickname={self._nickname!r}, score={self._score})"
