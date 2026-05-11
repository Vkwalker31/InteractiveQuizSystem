"""
Business logic services: Strategy (scoring), Singleton (GameManager), Observer (ConnectionManager).
"""

from services.scoring import ScoringStrategy, StaticScoring, FastestFingerScoring
from services.game_manager import GameManager
from services.connection_manager import ConnectionManager

__all__ = [
    "ScoringStrategy",
    "StaticScoring",
    "FastestFingerScoring",
    "GameManager",
    "ConnectionManager",
]
