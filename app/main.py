from __future__ import annotations

import json
import logging
import asyncio
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from app.models import (
    PinValidationResult,
    QuizCreate,
    QuizCreated,
    RuntimeStore,
    build_state_payload,
    parse_client_event,
)
from app.database import InMemoryQuizRepository, QuizDefinitionRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("interactive-quiz")

KAHOOT_TIME_DIVISOR_SEC = 15.0


def create_app(
    question_seconds: float = 15.0,
    leaderboard_seconds: float = 10.0,
    now_provider: callable | None = None,
    quiz_repository: QuizDefinitionRepository | None = None,
    uploads_dir: Path | None = None,
) -> FastAPI:
    if now_provider is None:
        now_provider = time.time
    app = FastAPI(title="Interactive Quiz System")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=r"https://.*\.(onrender\.com|trycloudflare\.com)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    base_dir = Path(__file__).resolve().parent.parent
    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")
    templates = Jinja2Templates(directory=str(base_dir / "templates"))
    upload_root = uploads_dir or (base_dir / "static" / "uploads")
    upload_root.mkdir(parents=True, exist_ok=True)

    app.state.runtime = RuntimeStore()
    # Исправлено: убрана аннотация типа для атрибута объекта, чтобы не было ошибки Pylance
    app.state.connections = {} 
    app.state.quiz_repo = quiz_repository or InMemoryQuizRepository()

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        mongo_ok = False
        try:
            mongo_ok = await app.state.quiz_repo.ping()
        except Exception:
            logger.exception("health check ping failed")
        status_code = 200 if mongo_ok else 503
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ok" if mongo_ok else "degraded",
                "mongo": "up" if mongo_ok else "down",
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error path=%s method=%s", request.url.path, request.method)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": str(exc)},
        )

    @app.post("/api/quizzes", response_model=QuizCreated, status_code=201)
    async def create_quiz(payload: QuizCreate) -> QuizCreated:
        quiz_id = await app.state.quiz_repo.save_quiz(payload)
        session = app.state.runtime.create_session(payload, quiz_id=quiz_id)
        logger.info("quiz created title=%s pin=%s", payload.title, session.pin)
        return QuizCreated(quiz_id=session.quiz_id, pin=session.pin)

    @app.put("/api/quizzes/{quiz_id}")
    async def update_quiz(quiz_id: str, payload: QuizCreate) -> dict[str, bool]:
        ok = await app.state.quiz_repo.update_quiz(quiz_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail="quiz_not_found")
        return {"ok": True}

    @app.delete("/api/quizzes/{quiz_id}")
    async def delete_quiz(quiz_id: str) -> dict[str, bool]:
        ok = await app.state.quiz_repo.delete_quiz(quiz_id)
        if not ok:
            raise HTTPException(status_code=404, detail="quiz_not_found")
        return {"ok": True}

    @app.get("/api/quizzes")
    async def list_quizzes() -> dict[str, list[dict]]:
        rows = await app.state.quiz_repo.list_quizzes()
        return {"items": rows}

    @app.post("/api/quizzes/{quiz_id}/sessions", response_model=QuizCreated, status_code=201)
    async def create_session_from_quiz(quiz_id: str) -> QuizCreated:
        stored = await app.state.quiz_repo.get_quiz(quiz_id)
        if not stored:
            raise HTTPException(status_code=404, detail="quiz_not_found")
        quiz_payload = QuizCreate.model_validate(
            {
                "title": stored.get("title", ""),
                "description": stored.get("description", ""),
                "questions": stored.get("questions", []),
            }
        )
        session = app.state.runtime.create_session(quiz_payload, quiz_id=quiz_id)
        logger.info("session created from quiz quiz_id=%s pin=%s", quiz_id, session.pin)
        return QuizCreated(quiz_id=session.quiz_id, pin=session.pin)

    @app.get("/api/quizzes/{quiz_id}")
    async def get_quiz_by_id(quiz_id: str) -> dict:
        quiz = await app.state.quiz_repo.get_quiz(quiz_id)
        if quiz is None:
            return {"found": False}
        return {"found": True, "quiz": quiz}

    @app.get("/api/sessions/{pin}/validate", response_model=PinValidationResult)
    async def validate_pin(pin: str) -> PinValidationResult:
        return PinValidationResult(pin=pin, valid=app.state.runtime.has_pin(pin))

    @app.post("/api/sessions/{pin}/close")
    async def close_session(pin: str) -> dict[str, bool]:
        """Remove runtime session (e.g. host returned to menu after game over)."""
        if app.state.runtime.has_pin(pin):
            app.state.runtime.sessions.pop(pin, None)
            app.state.connections.pop(pin, None)
            logger.info("session closed pin=%s", pin)
        return {"ok": True}

    @app.post("/api/upload")
    async def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
        suffix = Path(file.filename or "").suffix.lower() or ".bin"
        file_name = f"{uuid.uuid4().hex}{suffix}"
        target = upload_root / file_name
        content = await file.read()
        await asyncio.to_thread(target.write_bytes, content)
        static_prefix = "/static/uploads"
        if uploads_dir is not None:
            static_prefix = "/uploads-test"
        logger.info("upload saved file=%s size=%s", file_name, len(content))
        return {"url": f"{static_prefix}/{file_name}"}

    @app.get("/", response_class=HTMLResponse)
    async def player_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="player.html")

    @app.get("/host", response_class=HTMLResponse)
    async def host_home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="host_create.html")

    @app.get("/host/quiz/new", response_class=HTMLResponse)
    async def host_quiz_builder(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="host_quiz_builder.html")

    @app.get("/host/game/{pin}", response_class=HTMLResponse)
    async def host_game(request: Request, pin: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request, 
            name="host.html", 
            context={"pin": pin}
        )

    @app.websocket("/ws/{pin}/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, pin: str, client_id: str) -> None:
        client_id = str(client_id)
        if not app.state.runtime.has_pin(pin):
            await websocket.accept()
            await websocket.send_text(json.dumps({"event_type": "ERROR", "message": "Invalid PIN"}))
            await websocket.close(code=1008)
            return

        await websocket.accept()
        app.state.runtime.register_client(pin, client_id)
        app.state.connections.setdefault(pin, {})[client_id] = websocket
        logger.info("ws connected pin=%s client=%s", pin, client_id)
        await websocket.send_text(json.dumps({"event_type": "CONNECTED", "pin": pin, "client_id": client_id}))

        async def broadcast_state() -> None:
            session = app.state.runtime.sessions.get(pin)
            if not session:
                return

            payload: dict = build_state_payload(session)

            if payload.get("event_type") == "QUESTION_STATE":
                payload["question_seconds"] = question_seconds
                q_idx = session.question_index
                if 0 <= q_idx < len(session.questions):
                    q = session.questions[q_idx]
                    if "question_text" not in payload or not payload.get("question_text"):
                        payload["question_text"] = q.get("text", "")
                    if not payload.get("options"):
                        payload["options"] = q.get("options", [])
                    if q.get("image_url"):
                        payload["image_url"] = q.get("image_url")
            elif payload.get("event_type") == "LEADERBOARD_STATE":
                payload["leaderboard_seconds"] = leaderboard_seconds

            if payload.get("event_type") == "LOBBY_STATE":
                players_list = [{"nickname": nick} for nick in session.players.values()]
                payload["players"] = players_list
            dead_clients = []
            for cid, socket in app.state.connections.get(pin, {}).items():
                try:
                    out_payload = dict(payload)
                    if out_payload.get("event_type") == "LEADERBOARD_STATE":
                        is_correct = bool(session.last_answer_correct.get(cid, False))
                        points_delta = int(session.last_score_delta.get(cid, 0) or 0)
                        out_payload["is_correct"] = is_correct
                        out_payload["points_delta"] = points_delta
                    await socket.send_text(json.dumps(out_payload))
                except Exception:
                    dead_clients.append(cid)
            
            for dead in dead_clients:
                app.state.connections.get(pin, {}).pop(dead, None)

        def cancel_timers(session) -> None:
            if session.question_timer_task and not session.question_timer_task.done():
                session.question_timer_task.cancel()
            session.question_timer_task = None
            if session.leaderboard_timer_task and not session.leaderboard_timer_task.done():
                session.leaderboard_timer_task.cancel()
            session.leaderboard_timer_task = None

        async def set_state(session, state_name: str) -> None:
            logger.info("Setting state pin=%s state=%s", pin, state_name)
            cancel_timers(session)
            session.state = state_name
            if state_name == "question":
                session.answered_clients.clear()
                session.last_answer_correct.clear()
                session.last_score_delta.clear()
                session.question_started_at = float(now_provider())
            
            await broadcast_state()

            if state_name == "finished":
                ranking = sorted(
                    session.players.items(),
                    key=lambda item: (-session.scores.get(item[0], 0), item[1].lower()),
                )
                record = {
                    "pin": session.pin,
                    "quiz_id": session.quiz_id,
                    "title": session.title,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "leaderboard": [
                        {"nickname": nick, "score": session.scores.get(cid, 0)}
                        for cid, nick in ranking
                    ],
                }
                try:
                    await app.state.quiz_repo.save_session_history(record)
                except Exception:
                    logger.exception("save_session_history failed pin=%s", pin)

            if state_name == "question":
                q_index = session.question_index
                async def question_timeout():
                    try:
                        if question_seconds > 0:
                            await asyncio.sleep(question_seconds)
                        else:
                            await asyncio.sleep(0)
                        current = app.state.runtime.sessions.get(pin)
                        if current and current.state == "question" and current.question_index == q_index:
                            await set_state(current, "leaderboard")
                    except asyncio.CancelledError: pass
                session.question_timer_task = asyncio.create_task(question_timeout())
                await asyncio.sleep(0)

            elif state_name == "leaderboard":
                lb_index = session.question_index
                async def leaderboard_timeout():
                    try:
                        if leaderboard_seconds > 0:
                            await asyncio.sleep(leaderboard_seconds)
                        else:
                            await asyncio.sleep(0)
                        current = app.state.runtime.sessions.get(pin)
                        if not current or current.state != "leaderboard" or current.question_index != lb_index:
                            return
                        if current.question_index + 1 < current.total_questions:
                            current.question_index += 1
                            await set_state(current, "question")
                        else:
                            await set_state(current, "finished")
                    except asyncio.CancelledError: pass
                session.leaderboard_timer_task = asyncio.create_task(leaderboard_timeout())
                await asyncio.sleep(0)

        await broadcast_state()

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    logger.info("WS MESSAGE from %s: %s", client_id, msg) 
                except json.JSONDecodeError:
                    continue

                event = parse_client_event(msg)
                session = app.state.runtime.sessions.get(pin)
                if not session: break

                if event == "PING":
                    await websocket.send_text(json.dumps({"event_type": "PONG"}))
                
                elif event == "PLAYER_JOIN":
                    nickname = str(msg.get("nickname") or "Player").strip() or "Player"
                    session.players[client_id] = nickname
                    session.scores.setdefault(client_id, 0)
                    logger.info("Player joined: %s in pin %s", nickname, pin)
                    await broadcast_state()
                
                elif event == "HOST_ACTION":
                    action = str(msg.get("action") or "").strip()
                    logger.info("Host action received: %s", action)
                    
                    if action in ["start_question", "start"] and session.state == "lobby":
                        if len(session.players) == 0:
                            logger.info("start ignored: no players pin=%s", pin)
                            continue
                        session.question_index = 0
                        await set_state(session, "question")
                    
                    elif action == "next":
                        if session.state == "question":
                            await set_state(session, "leaderboard")
                        elif session.state == "leaderboard":
                            if session.question_index + 1 < session.total_questions:
                                session.question_index += 1
                                await set_state(session, "question")
                            else:
                                await set_state(session, "finished")
                
                elif event == "ANSWER_SUBMITTED":
                    if session.state != "question" or client_id in session.answered_clients:
                        continue
                    session.answered_clients.add(client_id)
                    try:
                        answer = int(msg.get("answer"))
                    except:
                        answer = -1
                    
                    correct_index = -1
                    if 0 <= session.question_index < len(session.question_correct_indexes):
                        correct_index = session.question_correct_indexes[session.question_index]
                    
                    if answer == correct_index:
                        started = session.question_started_at or float(now_provider())
                        elapsed_time = float(now_provider()) - float(started)
                        score_delta = int(max(0, 1000 * (1 - (elapsed_time / KAHOOT_TIME_DIVISOR_SEC))))
                        session.scores[client_id] = session.scores.get(client_id, 0) + score_delta
                        session.last_answer_correct[client_id] = True
                        session.last_score_delta[client_id] = score_delta
                    else:
                        session.last_answer_correct[client_id] = False
                        session.last_score_delta[client_id] = 0
                
                    if len(session.players) > 0 and len(session.answered_clients) >= len(session.players):
                        await set_state(session, "leaderboard")
                    else:
                        await broadcast_state()

        except WebSocketDisconnect:
            logger.info("ws disconnected pin=%s client=%s", pin, client_id)
            app.state.runtime.unregister_client(pin, client_id)
            app.state.connections.get(pin, {}).pop(client_id, None)
            sess = app.state.runtime.sessions.get(pin)
            if sess and client_id in sess.players:
                sess.players.pop(client_id, None)
                sess.answered_clients.discard(client_id)
                await broadcast_state()

    return app


app = create_app()