from fastapi.testclient import TestClient

from app.database import InMemoryQuizRepository
from app.main import create_app


def _recv_until_event(ws, event_type: str, max_reads: int = 14) -> dict:
    for _ in range(max_reads):
        payload = ws.receive_json()
        if payload.get("event_type") == event_type:
            return payload
    raise AssertionError(f"Did not receive {event_type!r}")


def _create_quiz(client: TestClient) -> str:
    response = client.post(
        "/api/quizzes",
        json={
            "title": "Scoring",
            "questions": [
                {"text": "Q1", "options": ["A", "B", "C", "D"], "correct_index": 2}
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["pin"]


def test_scoring_formula_uses_elapsed_ms() -> None:
    clock = [1000.0]
    app = create_app(
        question_seconds=10.0,
        leaderboard_seconds=10.0,
        now_provider=lambda: clock[0],
        quiz_repository=InMemoryQuizRepository(),
    )
    client = TestClient(app)
    pin = _create_quiz(client)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")
        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Neo"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(player_ws, "LOBBY_STATE")

        clock[0] = 1000.0
        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(player_ws, "QUESTION_STATE")

        clock[0] = 1002.0
        player_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 2})
        lb = _recv_until_event(host_ws, "LEADERBOARD_STATE")
        assert lb["leaderboard"][0]["nickname"] == "Neo"
        # elapsed_time = 2s, Kahoot formula with divisor 15: int(1000 * (1 - 2/15)) = 866
        assert lb["leaderboard"][0]["score"] == 866


def test_leaderboard_ordering_by_score_desc() -> None:
    # Strict call order of now_provider: question start, fast score, slow score (TestClient runs handlers predictably)
    times = iter([2000.0, 2000.5, 2002.0])

    def now_provider() -> float:
        return next(times)

    app = create_app(
        question_seconds=10.0,
        leaderboard_seconds=10.0,
        now_provider=now_provider,
        quiz_repository=InMemoryQuizRepository(),
    )
    client = TestClient(app)
    pin = _create_quiz(client)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/fast"
    ) as fast_ws, client.websocket_connect(f"/ws/{pin}/slow") as slow_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(fast_ws, "CONNECTED")
        _recv_until_event(slow_ws, "CONNECTED")
        fast_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Fast"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(fast_ws, "LOBBY_STATE")
        _recv_until_event(slow_ws, "LOBBY_STATE")
        slow_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Slow"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(fast_ws, "LOBBY_STATE")
        _recv_until_event(slow_ws, "LOBBY_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(fast_ws, "QUESTION_STATE")
        _recv_until_event(slow_ws, "QUESTION_STATE")

        fast_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 2})
        slow_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 2})

        lb = _recv_until_event(host_ws, "LEADERBOARD_STATE")
        assert lb["leaderboard"][0]["nickname"] == "Fast"
        assert lb["leaderboard"][1]["nickname"] == "Slow"
        assert lb["leaderboard"][0]["score"] == 966
        assert lb["leaderboard"][1]["score"] == 866


def test_tie_behavior_orders_by_nickname() -> None:
    clock = [3000.0]
    app = create_app(
        question_seconds=10.0,
        leaderboard_seconds=10.0,
        now_provider=lambda: clock[0],
        quiz_repository=InMemoryQuizRepository(),
    )
    client = TestClient(app)
    pin = _create_quiz(client)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/zed"
    ) as zed_ws, client.websocket_connect(f"/ws/{pin}/amy") as amy_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(zed_ws, "CONNECTED")
        _recv_until_event(amy_ws, "CONNECTED")
        zed_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Zed"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(zed_ws, "LOBBY_STATE")
        _recv_until_event(amy_ws, "LOBBY_STATE")
        amy_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Amy"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(zed_ws, "LOBBY_STATE")
        _recv_until_event(amy_ws, "LOBBY_STATE")

        clock[0] = 3000.0
        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(zed_ws, "QUESTION_STATE")
        _recv_until_event(amy_ws, "QUESTION_STATE")

        clock[0] = 3001.0
        zed_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 2})
        amy_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 2})

        lb = _recv_until_event(host_ws, "LEADERBOARD_STATE")
        assert lb["leaderboard"][0]["score"] == 933
        assert lb["leaderboard"][1]["score"] == 933
        assert lb["leaderboard"][0]["nickname"] == "Amy"
        assert lb["leaderboard"][1]["nickname"] == "Zed"

