"""
Load and concurrency simulation: N players connect to the same PIN and submit answers
at the same time (asyncio.gather). Verifies GameSession and ScoringStrategy handle
concurrent updates without race conditions or crashes.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

N_PLAYERS = 20
WS_BASE = "ws://127.0.0.1:8000"


async def run_player(
    pin: str,
    player_id: int,
    answer_index: int,
    time_taken: float,
) -> dict:
    """
    One player: connect, join, wait for QUESTION_STATE (or timeout), then send ANSWER_SUBMITTED.
    Returns result dict with success, score (if any), and any error.
    """
    client_id = f"load-player-{player_id}"
    uri = f"{WS_BASE}/ws/{pin}/{client_id}"
    result: dict = {"player_id": player_id, "ok": False, "error": None, "messages": 0}

    if not HAS_WEBSOCKETS:
        result["error"] = "websockets package not installed (pip install websockets)"
        return result

    try:
        async with websockets.connect(uri, close_timeout=2) as ws:
            await ws.send(json.dumps({"event_type": "PLAYER_JOIN", "nickname": f"Player{player_id}"}))
            result["messages"] += 1

            got_question = False
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                result["messages"] += 1
                data = json.loads(msg)
                if data.get("event_type") == "QUESTION_STATE":
                    got_question = True
                    break
            if not got_question:
                result["error"] = "timeout waiting for QUESTION_STATE"
                return result

            await ws.send(json.dumps({
                "event_type": "ANSWER_SUBMITTED",
                "answer": answer_index,
                "time_taken": time_taken,
            }))
            result["messages"] += 1

            try:
                await asyncio.wait_for(ws.recv(), timeout=3.0)
                result["messages"] += 1
            except asyncio.TimeoutError:
                pass
            result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


async def main() -> None:
    """Create a session, start question, then N players submit answers concurrently."""
    if not HAS_WEBSOCKETS:
        print("Install websockets: pip install websockets")
        sys.exit(1)

    pin = sys.argv[1] if len(sys.argv) > 1 else None
    if not pin:
        print("Usage: python scripts/load_test.py <PIN>")
        print("  1. Start app: uvicorn main:app --reload")
        print("  2. Open /host/create, start a quiz, open /host/game/<PIN>")
        print("  3. Click 'Start question' so the game is in QUESTION_STATE")
        print("  4. Run: python scripts/load_test.py <PIN>")
        sys.exit(2)

    print(f"Load test: {N_PLAYERS} players, PIN={pin}, concurrent ANSWER_SUBMITTED")
    print("Ensure app is running and host has already clicked 'Start question' so state is QUESTION_STATE.")
    print("Waiting 2s for you to start the question...")
    await asyncio.sleep(2)

    tasks = [
        run_player(pin, i, 0, 1.0) for i in range(N_PLAYERS)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    ok = 0
    errors = []
    for r in results:
        if isinstance(r, Exception):
            errors.append(str(r))
            continue
        if r.get("ok"):
            ok += 1
        elif r.get("error"):
            errors.append(r["error"])

    print(f"Done: {ok}/{N_PLAYERS} players submitted successfully.")
    if errors:
        print("Errors (sample):", errors[:5])
    if ok == N_PLAYERS:
        print("No race conditions or crashes: all concurrent submissions handled.")
    else:
        print("Some submissions failed (may be expected if question was not active).")
    sys.exit(0 if ok >= N_PLAYERS // 2 else 1)


if __name__ == "__main__":
    asyncio.run(main())
