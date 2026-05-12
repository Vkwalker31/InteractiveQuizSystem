# Interactive Quiz System

## **1. PROJECT OVERVIEW**

### **Description**

**Interactive Quiz System** is a **real-time, Kahoot-inspired quiz platform** built with **FastAPI** and **WebSockets**. A host runs a live session; players join with a **PIN**, answer timed questions, and see results on a **shared leaderboard**, ending on a **final podium** view.

### **Key features**

- **Real-time multiplayer** — Many players in one session; lobby and game events stay synchronized over WebSockets.
- **Dynamic quiz builder (CRUD)** — Create, read, update, and delete quizzes through the host UI and REST API.
- **Automated game flow** — Server-driven phases: lobby, active question, leaderboard between questions, and finished state.
- **Time-based scoring** — Points for correct answers depend on how quickly the player responds (see [Mathematical models](#4-mathematical-models)).
- **Dynamic answer counts (2–4)** — Each question supports **two to four** options; the UI renders the appropriate grid.
- **Final podium** — After the last question, the **FINISHED** state presents ranked winners (podium-style UI for players).

---

## **2. ARCHITECTURE & TECH STACK**

| Area | Stack |
|------|--------|
| **Backend** | **Python**, **FastAPI**, **WebSockets** for bidirectional communication between host, players, and the server |
| **Database** | **MongoDB** with the **Motor** async driver for persisting quiz definitions and session-related data |
| **Frontend** | **Vanilla JavaScript** (modular **UIManager** together with **GameEngine** and **SocketClient**), **HTML5**, **CSS3** — modern UI with layout polish and CSS-driven animations |
| **State management** | **Server-side source of truth** — session phase, timers, scores, and rankings are authoritative on the server; clients apply incoming events |

**Typical split:** HTTP for quiz CRUD, uploads, and starting sessions; WebSockets (`/ws/...`) for live gameplay messages (`LOBBY_STATE`, `QUESTION_STATE`, `LEADERBOARD_STATE`, `FINISHED_STATE`).

---

## **3. DESIGN PATTERNS & PRINCIPLES**

- **State machine pattern** — Gameplay is modeled as explicit phases with controlled transitions: **LOBBY** → **QUESTION** → **LEADERBOARD** → **FINISHED** (see `state/` and session handling in `app/`).
- **Observer pattern** — Implemented via **WebSockets**: when the session changes, the server **broadcasts** payloads so every connected client receives the same update without polling.
- **Repository pattern** — MongoDB access is **abstracted** behind repository-style layers (see `app/database.py` and `repository/`), so HTTP and WebSocket code do not embed raw query details.
- **TDD (test-driven development)** — Core behavior is covered by **pytest** **unit** and **integration** tests under `tests/` (API, WebSockets, timers, scoring, persistence).

---

## **4. MATHEMATICAL MODELS**

### **Scoring formula**

For a **correct** answer, let **t** be the **response time in seconds** (from question start until the answer is accepted). The point value is:

$$
S = \left\lfloor \max \left( 0, 1000 \cdot \left( 1 - \frac{t}{15} \right) \right) \right\rfloor
$$

In code terms, **`int(...)`** truncates toward zero; for non‑negative values this matches **flooring** the linear decay. **Incorrect** answers add **0** points for that question.

**Behavior in short:**

| Response time **t** | Effect |
|---------------------|--------|
| **t = 0** | Maximum **1000** points |
| **0 < t < 15** | Linear decrease toward **0** |
| **t ≥ 15** | **0** points (still capped at ≥ 0 by **`max`** before **`int`**) |

### **Leaderboard logic (cumulative scores)**

- Each player’s row shows a **cumulative score**: the **sum** of all points earned in the session so far.
- Rankings are by **total score** (**higher** first). When totals tie, ordering uses a **stable secondary key** (e.g. nickname lexicographic order) so the table is deterministic.
- The same cumulative ordering applies to **mid-game leaderboards** and the **final podium** in **FINISHED** state.

---

## **5. PROJECT STRUCTURE**

Main application package, templates, static assets, tests, and domain models:

```text
InteractiveQuizSystem/
├── main.py                  # Re-exports FastAPI `app` for `uvicorn main:app`
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes, WebSocket handlers
│   ├── models.py            # Pydantic models + session payload helpers
│   └── database.py          # Quiz repository (MongoDB / in-memory for tests)
├── models/                  # Domain entities (quiz, questions, player, session)
├── state/                   # State-machine-oriented game phases
├── services/                # Game manager, connections, quiz creation helpers
├── repository/              # MongoDB wiring, mappers, base repository
├── templates/               # HTML (Jinja2)
│   ├── base.html
│   ├── host.html
│   ├── host_create.html
│   ├── host_quiz_builder.html
│   └── player.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── modules/
│           ├── GameEngine.js
│           ├── SocketClient.js
│           └── UIManager.js
├── tests/                   # pytest — API, WebSockets, scoring, timers, …
├── scripts/
│   ├── seed_db.py
│   └── load_test.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── README.md
```

---

## **6. INSTALLATION & SETUP**

### **Prerequisites**

- **Python 3.9+**
- **MongoDB** (local, Docker, or hosted)

### **Step-by-step**

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd InteractiveQuizSystem
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   (Using a virtual environment is recommended: `python -m venv .venv` then activate it before `pip install`.)

3. **Environment variables — `MONGO_URI`**

   Set **`MONGO_URI`** to your MongoDB connection string, for example:

   ```bash
   set MONGO_URI=mongodb://127.0.0.1:27017
   ```

   ```bash
   export MONGO_URI=mongodb://127.0.0.1:27017
   ```

   Optional: **`MONGODB_DATABASE`** selects the database name (default **`quiz_system`**). The code also accepts **`MONGODB_URI`** if you prefer that name; **`MONGO_URI`** is checked when **`MONGODB_URI`** is unset.

4. **Run the app**

   From the **project root**:

   ```bash
   uvicorn main:app --reload
   ```

   Open **http://127.0.0.1:8000** in a browser.  
   **Alternative (same app):** `uvicorn app.main:app --reload` — useful if you skip the root `main.py` shim.

### **Docker (optional)**

```bash
docker compose up --build
```

Uses **`docker-compose.yml`** (MongoDB + web on port **8000**, etc.).

---

## **7. TESTING**

From the **repository root**, run:

```bash
pytest
```

Examples:

```bash
pytest -q                      # Less noise
pytest tests/test_api.py       # One file
pytest -k "scoring or timer"   # Name filter
```

Tests use **pytest** together with Starlette’s **TestClient** and WebSocket support to validate HTTP and real-time flows without a manual browser session.

---

## **8. GAME FLOW INSTRUCTIONS**

### **Create a quiz (CRUD)**

1. Go to **`/host`** (host console).
2. Open **Create quiz** → **`/host/quiz/new`**.
3. Enter metadata and **2–4** options per question; mark the **correct** option.
4. Save — the quiz is stored via the REST API (**list / create / update / delete** as exposed by the backend).

### **Launch a session and share the PIN**

1. On **`/host`**, pick a saved quiz and **Start session** ( **`POST /api/quizzes/{quiz_id}/sessions`** ).
2. The response includes a **six-digit PIN** — share it with players (verbally or with a link that pre-fills the PIN).
3. Open **`/host/game/{PIN}`** on the host machine to drive the game (host WebSocket: **`/ws/{pin}/host`**).

### **Automated transition logic**

- **Questions:** default **15 seconds** per question phase — countdown in the UI; the server advances when the timer elapses or when all players have answered (per server rules in `app/main.py`).
- **Leaderboards:** default **10 seconds** after each question — then auto-advance to the **next question** or **FINISHED** / podium.

Timers may also be sent explicitly in WebSocket payloads (e.g. `question_seconds`, `leaderboard_seconds`); the client falls back to **15** / **10** when omitted.

### **Players**

- **`/player`** — enter **PIN** and **nickname**, then play. Optional query **`?pin=xxxxxx`** can pre-fill the PIN.

---