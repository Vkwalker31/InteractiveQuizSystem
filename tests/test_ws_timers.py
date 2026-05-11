import time

from fastapi.testclient import TestClient

from app.main import create_app


def _recv_until_event(ws, event_type: str, max_reads: int = 24) -> dict:
    for _ in range(max_reads):
        payload = ws.receive_json()
        if payload.get("event_type") == event_type:
            return payload
    raise AssertionError(f"Did not receive {event_type!r}")


def _create_quiz(client: TestClient, n_questions: int = 1) -> str:
    questions = []
    for idx in range(n_questions):
        questions.append(
            {"text": f"Q{idx}", "options": ["A", "B", "C", "D"], "correct_index": 0}
        )
    response = client.post("/api/quizzes", json={"title": "Timed", "questions": questions})
    assert response.status_code == 201
    return response.json()["pin"]


def test_question_auto_transitions_to_leaderboard_after_timeout() -> None:
    # question_seconds=0 → server uses asyncio.sleep(0) only (reliable with TestClient)
    app = create_app(question_seconds=0.0, leaderboard_seconds=10.0)
    client = TestClient(app)
    pin = _create_quiz(client, n_questions=1)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")
        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Neo"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(player_ws, "LOBBY_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(player_ws, "QUESTION_STATE")

        host_lb = _recv_until_event(host_ws, "LEADERBOARD_STATE")
        player_lb = _recv_until_event(player_ws, "LEADERBOARD_STATE")
        assert host_lb["event_type"] == "LEADERBOARD_STATE"
        assert player_lb["event_type"] == "LEADERBOARD_STATE"


def test_leaderboard_auto_transitions_to_next_question() -> None:
    app = create_app(question_seconds=0.0, leaderboard_seconds=0.0)
    client = TestClient(app)
    pin = _create_quiz(client, n_questions=2)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")
        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Trinity"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(player_ws, "LOBBY_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(player_ws, "QUESTION_STATE")

        _recv_until_event(host_ws, "LEADERBOARD_STATE")
        _recv_until_event(player_ws, "LEADERBOARD_STATE")
        host_q2 = _recv_until_event(host_ws, "QUESTION_STATE")
        player_q2 = _recv_until_event(player_ws, "QUESTION_STATE")
        assert host_q2["question_index"] == 1
        assert player_q2["question_index"] == 1


def test_manual_next_cancels_question_timer_task() -> None:
    # Long question timer: host triggers next manually before timeout
    app = create_app(question_seconds=999.0, leaderboard_seconds=3.0)
    client = TestClient(app)
    pin = _create_quiz(client, n_questions=1)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")
        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Morpheus"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(player_ws, "LOBBY_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        _recv_until_event(host_ws, "QUESTION_STATE")
        _recv_until_event(player_ws, "QUESTION_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "next"})
        _recv_until_event(host_ws, "LEADERBOARD_STATE")
        _recv_until_event(player_ws, "LEADERBOARD_STATE")

        time.sleep(0.25)
        host_ws.send_json({"event_type": "PING"})
        while True:
            msg = host_ws.receive_json()
            if msg.get("event_type") == "PONG":
                break
