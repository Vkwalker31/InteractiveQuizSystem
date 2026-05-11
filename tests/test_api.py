from fastapi.testclient import TestClient

from app.database import InMemoryQuizRepository
from app.main import create_app


def test_quiz_creation_returns_pin_and_quiz_id() -> None:
    client = TestClient(create_app(quiz_repository=InMemoryQuizRepository()))
    payload = {
        "title": "Space Quiz",
        "description": "Smoke",
        "questions": [
            {"text": "2+2?", "options": ["3", "4", "5", "6"], "correct_index": 1}
        ],
    }
    response = client.post("/api/quizzes", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["pin"]) == 6
    assert data["pin"].isdigit()
    assert len(data["quiz_id"]) > 10


def test_pin_validation_endpoint() -> None:
    client = TestClient(create_app(quiz_repository=InMemoryQuizRepository()))
    create_resp = client.post(
        "/api/quizzes",
        json={
            "title": "PIN test",
            "questions": [
                {"text": "A?", "options": ["A", "B", "C", "D"], "correct_index": 0}
            ],
        },
    )
    pin = create_resp.json()["pin"]
    valid_resp = client.get(f"/api/sessions/{pin}/validate")
    invalid_resp = client.get("/api/sessions/999999/validate")
    assert valid_resp.status_code == 200
    assert valid_resp.json() == {"pin": pin, "valid": True}
    assert invalid_resp.status_code == 200
    assert invalid_resp.json() == {"pin": "999999", "valid": False}


def test_websocket_handshake_for_valid_pin() -> None:
    client = TestClient(create_app())
    create_resp = client.post(
        "/api/quizzes",
        json={
            "title": "WS",
            "questions": [
                {"text": "Q", "options": ["1", "2", "3", "4"], "correct_index": 0}
            ],
        },
    )
    pin = create_resp.json()["pin"]
    with client.websocket_connect(f"/ws/{pin}/client-1") as websocket:
        connected = websocket.receive_json()
        assert connected["event_type"] == "CONNECTED"
        lobby = websocket.receive_json()
        assert lobby["event_type"] == "LOBBY_STATE"
        websocket.send_json({"event_type": "PING"})
        pong = websocket.receive_json()
        assert pong["event_type"] == "PONG"


def test_healthcheck_reports_repository_status() -> None:
    client = TestClient(create_app(quiz_repository=InMemoryQuizRepository()))
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongo": "up"}


def test_upload_endpoint_saves_file_and_returns_url(tmp_path) -> None:
    client = TestClient(
        create_app(uploads_dir=tmp_path, quiz_repository=InMemoryQuizRepository())
    )
    file_content = b"\x89PNG\r\n\x1a\nfake-image-content"
    response = client.post(
        "/api/upload",
        files={"file": ("question.png", file_content, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    file_name = data["url"].split("/")[-1]
    saved_path = tmp_path / file_name
    assert saved_path.exists()
    assert saved_path.read_bytes() == file_content

