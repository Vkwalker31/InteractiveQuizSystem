from fastapi.testclient import TestClient

from app.main import create_app


def _recv_until_event(ws, event_type: str, max_reads: int = 8) -> dict:
    for _ in range(max_reads):
        payload = ws.receive_json()
        if payload.get("event_type") == event_type:
            return payload
    raise AssertionError(f"Did not receive {event_type!r}")


def _recv_lobby_with_player_count(ws, expected: int, max_reads: int = 20) -> dict:
    for _ in range(max_reads):
        payload = ws.receive_json()
        if payload.get("event_type") == "LOBBY_STATE" and payload.get("player_count") == expected:
            return payload
    raise AssertionError(f"No LOBBY_STATE with player_count={expected}")


def _create_single_question_quiz(client: TestClient) -> str:
    response = client.post(
        "/api/quizzes",
        json={
            "title": "Flow quiz",
            "questions": [
                {"text": "Q?", "options": ["A", "B", "C", "D"], "correct_index": 0}
            ],
        },
    )
    assert response.status_code == 201
    return response.json()["pin"]


def test_join_broadcasts_lobby_state_to_host_and_player() -> None:
    client = TestClient(create_app())
    pin = _create_single_question_quiz(client)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")

        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Neo"})
        host_state = _recv_lobby_with_player_count(host_ws, 1)
        player_state = _recv_lobby_with_player_count(player_ws, 1)

        assert host_state["player_count"] == 1
        assert player_state["player_count"] == 1
        assert host_state["players"][0]["nickname"] == "Neo"
        assert player_state["players"][0]["nickname"] == "Neo"


def test_state_transitions_lobby_question_leaderboard_finished() -> None:
    client = TestClient(create_app())
    pin = _create_single_question_quiz(client)

    with client.websocket_connect(f"/ws/{pin}/host") as host_ws, client.websocket_connect(
        f"/ws/{pin}/player-1"
    ) as player_ws:
        _recv_until_event(host_ws, "CONNECTED")
        _recv_until_event(player_ws, "CONNECTED")

        player_ws.send_json({"event_type": "PLAYER_JOIN", "nickname": "Trinity"})
        _recv_until_event(host_ws, "LOBBY_STATE")
        _recv_until_event(player_ws, "LOBBY_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "start_question"})
        host_question = _recv_until_event(host_ws, "QUESTION_STATE")
        player_question = _recv_until_event(player_ws, "QUESTION_STATE")
        assert host_question["question_index"] == 0
        assert player_question["question_index"] == 0

        player_ws.send_json({"event_type": "ANSWER_SUBMITTED", "answer": 0})
        _recv_until_event(host_ws, "LEADERBOARD_STATE")
        _recv_until_event(player_ws, "LEADERBOARD_STATE")

        host_ws.send_json({"event_type": "HOST_ACTION", "action": "next"})
        host_finished = _recv_until_event(host_ws, "FINISHED_STATE")
        player_finished = _recv_until_event(player_ws, "FINISHED_STATE")
        assert host_finished["event_type"] == "FINISHED_STATE"
        assert player_finished["event_type"] == "FINISHED_STATE"

