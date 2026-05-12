# Explanatory Note: Technical Documentation

**Subject:** Interactive Quiz System — Architecture, Implementation, and Quality Assurance  

**Document type:** Technical specification and explanatory memorandum  

**Audience:** Academic examination boards, engineering reviewers, and maintainers  

---

## 1. Project Requirements

### 1.1 Functional Requirements

The Interactive Quiz System is a real-time quiz platform. The following functional requirements are derived from the implemented behavior (host console, player client, REST API, and WebSocket protocol).

**Host role**

| Identifier | Requirement |
|------------|-------------|
| FR-H1 | The host shall create, read, update, and delete quizzes (**CRUD**) via the web interface and/or HTTP API, including questions with configurable answer sets (typically two to four options) and metadata (title, description). |
| FR-H2 | The host shall start a **live session** for a selected quiz, obtaining a **session PIN** that uniquely identifies the runtime game room. |
| FR-H3 | The host shall **control the session**: advance from lobby to active question, from question phase to leaderboard, and between rounds until the session terminates in a **finished** state (final podium). |
| FR-H4 | The host shall receive the same **canonical state payloads** as players (e.g. `LOBBY_STATE`, `QUESTION_STATE`, `LEADERBOARD_STATE`, `FINISHED_STATE`) over a dedicated WebSocket role (e.g. `/ws/{pin}/host`). |

**Player role**

| Identifier | Requirement |
|------------|-------------|
| FR-P1 | A player shall **join in real time** by supplying the session PIN and a display nickname, establishing a WebSocket connection scoped to that PIN. |
| FR-P2 | During an active question, the player shall submit **exactly one** answer per question (indexed choice model); duplicate submissions for the same question shall not alter scoring logic adversely. |
| FR-P3 | The player interface shall render **synchronized** question text, options, optional media, timers, and feedback derived entirely from server messages. |

**System role**

| Identifier | Requirement |
|------------|-------------|
| FR-S1 | The system shall maintain a **leaderboard** (ranked list) based on **cumulative scores** after each scored phase, with deterministic tie-breaking (e.g. secondary sort by nickname). |
| FR-S2 | The system shall enforce **automated timers** for question and leaderboard phases (configurable durations; defaults align with a 15-second question window and a 10-second leaderboard window in the client, with server-side scheduling via `asyncio` tasks where implemented). |
| FR-S3 | The system shall **broadcast** state changes to all connected clients for a given PIN so that every observer sees a consistent view of the game. |

### 1.2 Non-Functional Requirements

| Identifier | Category | Requirement |
|------------|----------|-------------|
| NFR-1 | **Scalability** | The architecture shall separate **long-lived quiz definitions** (MongoDB) from **ephemeral session state** (in-memory runtime store) so that horizontal scaling strategies can distinguish persistent writes from per-server session affinity. |
| NFR-2 | **Latency** | Real-time updates shall be delivered over **WebSockets** using asynchronous I/O, minimizing polling and reducing perceived latency for join, answer, and phase transitions. |
| NFR-3 | **Persistence** | Quiz content and, where enabled, session history shall be stored in **MongoDB** using the **Motor** asynchronous driver, abstracted behind repository-style components. |
| NFR-4 | **Maintainability** | Core domain logic (questions, session lifecycle) shall be expressed with explicit **object-oriented** abstractions (states, question subtypes) and covered by **automated tests**. |
| NFR-5 | **Reliability** | WebSocket broadcast paths shall tolerate failed sends by pruning **dead** connections without terminating the entire session (`ConnectionManager.broadcast`). |

---

## 2. Object-Oriented Design Theory and Architectural Approaches

### 2.1 State Pattern for Game Phases

The **State pattern** delegates behavior that depends on the current phase of a session to a dedicated object, rather than encoding phase logic as large conditional structures on a monolithic session class.

In this project, `GameState` (`state/game_state.py`) defines the abstract interface: `state_name`, lifecycle hooks (`on_enter`, `on_leave`), capability predicates (`can_start_question`, `can_show_leaderboard`, `can_go_next`), and `get_next_state` for lawful transitions. Concrete implementations include:

- `LobbyState` — initial phase; may transition to `QuestionState` when the host starts the first question.  
- `QuestionState` — active answering; may transition to `LeaderboardState`.  
- `LeaderboardState` — post-question ranking; may advance the question index and return to `QuestionState`, or enter `FinishedState`.  
- `FinishedState` — terminal phase; no further transitions.

The **context** object, `GameSession` (`models/game_session.py`), holds a reference to the current `GameState` and performs transitions via `transition_to`, invoking `on_leave` / `on_enter` and an optional **broadcast callback** so that all WebSocket clients are notified when the phase changes.

**Rationale:** The State pattern localizes transition rules per phase, satisfies the **open/closed** principle (new phases can be added by introducing new subclasses), and keeps `GameSession` readable while the number of host-triggered actions grows.

### 2.2 Repository Pattern for Database Abstraction

The **Repository pattern** mediates between the domain model and persistence technology so that application code depends on a **stable contract** rather than on MongoDB wire formats.

The project provides:

- `BaseRepository` (`repository/base_repository.py`) — abstract generic repository with `collection_name`, `get_collection()`, and CRUD-style method signatures (`find_by_id`, `insert`, …) backed by `motor` collections.  
- `QuizRepository` (`repository/quiz_repository.py`) — concrete persistence for `Quiz` aggregates, delegating document mapping to `QuizMapper`.  
- `MongoQuizRepository` / protocol-oriented access in `app/database.py` — alternative abstraction for quiz definitions used by the FastAPI application layer, again isolating BSON documents from route handlers.

**Rationale:** Repositories enable **unit testing** with in-memory substitutes, simplify migration to alternative storage, and centralize **ObjectId** handling and serialization rules.

### 2.3 Observer Pattern and WebSocket Broadcasts

Structurally, the **Observer pattern** describes a one-to-many dependency: when one object’s state changes, dependents are notified automatically.

Here, the **subject** is effectively the **live session state** (question index, scores, phase). **Observers** are the connected WebSocket clients (host and players) for a given PIN. The `ConnectionManager` (`services/connection_manager.py`) maintains `pin → { client_id → WebSocket }` and implements `broadcast(pin, message)`, which iterates all sockets and `await`s `send_text` for each subscriber.

`GameSession` supports a `set_broadcast_callback` hook invoked after `transition_to`, coupling the **state change** (domain) to the **notification** (infrastructure) without embedding socket details inside state classes.

**Rationale:** This design preserves **separation of concerns** while guaranteeing that every participant receives the same JSON payload shape after each transition.

### 2.4 Clean Architecture and Layering

Although the codebase evolved with both a **rich domain package** (`models/`, `state/`, `services/`, `repository/`) and a **slimmer runtime model** under `app/` (e.g. `SessionState`, Pydantic DTOs), the overall intent aligns with **Clean Architecture** principles:

| Layer | Responsibility | Representative modules |
|-------|----------------|-------------------------|
| **Presentation / adapters** | HTTP routes, WebSocket endpoint, Jinja2 templates, static assets | `app/main.py`, `templates/`, `static/` |
| **Application / use cases** | Orchestrating sessions, PIN generation, quiz creation flows | `services/game_manager.py`, `services/quiz_creator_service.py` |
| **Domain** | Entities and phase rules independent of transport | `models/`, `state/` |
| **Infrastructure** | MongoDB, Motor, file uploads, connection registry | `repository/`, `repository/mongo_database.py`, `app/database.py`, `ConnectionManager` |

**Dependency rule:** inner layers (domain) do not import FastAPI or Motor; outward layers depend inward. Where duplication exists between `GameSession` + `GameState` and `app/models.py` runtime structures, maintainers should treat that as a known **bounded context** boundary between “domain simulation / legacy richness” and “ASGI-first runtime,” and converge gradually if consolidation is required.

---

## 3. Application Development (Practical Implementation)

### 3.1 Object-Oriented Principles in Question and State Classes

**Encapsulation**

- `BaseQuestion` stores `_text`, `_time_limit_seconds`, and `_question_id` as protected implementation details and exposes them via **read-only or controlled properties** (`text`, `time_limit_seconds`, `question_id`).  
- `ChoiceQuestion` encapsulates `_options` and `_correct_index`, validating indices at construction time.  
- `GameSession` encapsulates `_players`, `_state`, and `_current_question_answered`, exposing behavior through methods such as `record_answer`, `transition_to`, and `trigger_next` instead of permitting unconstrained mutation from outside.

**Inheritance**

- `ChoiceQuestion` and `TrueFalseQuestion` **extend** `BaseQuestion`, reusing common initialization and the abstract contract while specializing storage and validation.  
- `LobbyState`, `QuestionState`, `LeaderboardState`, and `FinishedState` **extend** `GameState`, inheriting default no-op hooks where appropriate and overriding transition predicates and `get_next_state`.

**Polymorphism**

- Callers depend on `BaseQuestion` and invoke **`validate_answer`** and **`to_mappable_dict`** without branching on concrete types at every call site—the runtime subtype determines behavior.  
- `GameSession` interacts with the current object through the **`GameState`** interface: `can_go_next`, `get_next_state`, and lifecycle methods are dispatched polymorphically.

### 3.2 Scoring Algorithm

For a **correct** response, let $$t$$ denote the player’s **response time in seconds** measured from the instant the question becomes active until the server records the answer. The implemented Kahoot-style linear decay (see `tests/test_scoring_flow.py` for regression coverage) is:

$$
\text{score} = \operatorname{int}\left(\max\left(0,\ 1000 \cdot \left(1 - \frac{t}{15}\right)\right)\right)
$$

**Properties:**

- For $$t = 0$$, the expression inside the maximum is $$1000$$, yielding the maximum per-question reward.  
- For $$0 < t < 15$$, the reward decreases **linearly** with $$t$$.  
- For $$t \geq 15$$, the inner term is non-positive, hence the $$\max$$ with zero yields **zero** points before truncation.

Incorrect answers contribute **zero** points for that question. Cumulative standing is the sum of per-question awards across the session; leaderboard ordering uses descending total score and a secondary key for stability (see `app/models.py`, `build_state_payload` ranking).

### 3.3 Real-Time Synchronization: `asyncio` and WebSockets

Real-time behavior relies on **cooperative multitasking** in Python’s **`asyncio`** event loop combined with **Starlette/FastAPI WebSocket** handlers (asynchronous coroutines).

**Concurrency model**

- Each WebSocket connection is typically handled as an **`async`** coroutine; while one client awaits I/O, others can progress, which is essential when many players submit answers in a short interval.  
- The `ConnectionManager.broadcast` method **awaits** `websocket.send_text` sequentially per client; failed sends collect “dead” client IDs and remove them after the loop, preventing a single broken socket from blocking cleanup indefinitely.

**Timers**

- The runtime session model in `app/models.py` declares `question_timer_task` and `leaderboard_timer_task` as `asyncio.Task` references, indicating that phase deadlines are enforced using **scheduled asynchronous tasks** (e.g. `asyncio.create_task` combined with `asyncio.sleep` patterns in the application entrypoint).

**Consistency**

- The **server** computes authoritative scores and phase transitions; clients render payloads (`QUESTION_STATE`, `LEADERBOARD_STATE`, etc.) without locally inferring game rules, which avoids **split-brain** inconsistencies between browsers.

---

## 4. Deployment and Testing

### 4.1 Test-Driven Development (TDD)

During development, **pytest**-driven specifications were used to lock down behavior before or alongside feature growth:

- **API contracts** — HTTP status codes, JSON shapes, and quiz creation side effects (`tests/test_api.py`).  
- **WebSocket flows** — end-to-end sequences for host and player sockets (`tests/test_ws_game_flow.py`).  
- **Timers** — deterministic or controlled timing via injectable clock providers in `create_app` (`tests/test_ws_timers.py`).  
- **Scoring** — numeric expectations for the decay formula and ordering (`tests/test_scoring_flow.py`).  
- **Persistence** — repository and storage integration where applicable (`tests/test_persistence.py`).

This approach reduces regression risk when refactoring state transitions or repository mappings.

### 4.2 Testing Strategy

| Level | Objective | Examples in repository |
|-------|-------------|-------------------------|
| **Unit / focused logic** | Pure functions, scoring math, state predicates, mappers | Scoring tests with synthetic clocks |
| **Integration** | FastAPI `TestClient`, WebSocket handshake, multi-message flows | `test_ws_game_flow.py`, `test_ws_timers.py` |
| **Load / exploratory** | Concurrent synthetic players | `scripts/load_test.py` (asyncio + `websockets` client) |

Integration tests favor **in-memory** or **test-scoped** dependencies where `create_app` allows substitution of repositories and timing providers, isolating failures to the layer under examination.

### 4.3 Deployment with Docker and Environment Configuration

**Container image**

The `Dockerfile` builds a slim Python **3.10** image, installs `requirements.txt`, copies the application tree, exposes port **8000**, and launches:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

A **single worker** is appropriate when in-memory session registries must remain coherent on one process; scaling out requires a **sticky session** or external session store (future work).

**Compose stack**

`docker-compose.yml` orchestrates MongoDB (with health checks), the web service, optional upload volume mounts, and may include auxiliary services (e.g. tunneling) depending on deployment needs.

**Environment variables**

- **`MONGO_URI`** or **`MONGODB_URI`** — MongoDB connection string (the application resolves `MONGODB_URI` first, then `MONGO_URI`, with a localhost default—see `app/database.py`).  
- **`MONGODB_DATABASE`** — logical database name (default `quiz_system`).

Secrets and connection strings should be supplied via **environment** or **Docker secrets**, not committed to version control.

---

## 5. Results Analysis and Conclusion

### 5.1 Performance and Concurrency

The system is designed for **classroom-scale** concurrency: dozens of simultaneous connections per PIN are realistic on a single modest host, especially when the event loop is not blocked by synchronous CPU-heavy work. The `scripts/load_test.py` utility illustrates a **multi-client** scenario (default on the order of twenty concurrent players) issuing WebSocket traffic against a running instance.

**Observations:**

- Broadcast cost grows **linearly** with the number of connected clients for a PIN, as each `send_text` is awaited in series; for very large audiences, **sharding** or **message batching** strategies may be investigated.  
- MongoDB operations for quiz CRUD are **asynchronous**; under burst traffic, connection pooling (Motor) amortizes handshake overhead.

Formal throughput benchmarks are deployment-specific; production characterization should record **p50/p95 latency** for `PLAYER_JOIN`, `ANSWER_SUBMITTED`, and phase transition broadcasts under representative load.

### 5.2 Impact of Chosen Patterns on Maintainability and Evolution

The **State pattern** localized phase rules and made it straightforward to reason about **which host actions are legal** in each phase without nested `if/elif` chains across the entire codebase.

The **Repository pattern** insulated MongoDB BSON details from higher layers, simplifying **schema migration** and enabling **test doubles**.

The **Observer-style broadcast** through `ConnectionManager` decoupled socket fan-out from domain state objects, preserving **single responsibility** while keeping the user experience synchronized.

Together, these choices support **incremental scaling** of features (e.g. new question types via subclasses of `BaseQuestion`, new phases via `GameState` subclasses) with a contained blast radius for defects.

### 5.3 Achieved Goals and Future Improvements

**Achieved goals**

- Real-time multiplayer quiz sessions with **PIN-based** join.  
- **CRUD** for quizzes with persistence in MongoDB.  
- **Automated** phase progression and **time-aware** scoring.  
- **Architectural documentation** grounded in explicit patterns (State, Repository, Observer) and layered responsibilities.

**Potential improvements**

- **Distributed session store** (e.g. Redis) to enable multi-worker or multi-node deployments without losing ephemeral session state.  
- **Horizontal scaling** of WebSocket layers with a **pub/sub** bus for cross-node broadcasts.  
- **Unification** of the `GameSession`/`GameState` domain model with the `app/` runtime model to eliminate parallel representations.  
- **Structured observability** (metrics, tracing) for WebSocket latency and MongoDB slow queries in production.

---
