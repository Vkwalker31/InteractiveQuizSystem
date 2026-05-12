export class GameEngine {
  constructor({ ui, ws, mode, nickname = "Player" }) {
    this.ui = ui;
    this.ws = ws;
    this.mode = mode;
    this.nickname = nickname;
    this.currentState = "idle";
    this.currentQuestionId = null;
    this.answeredCurrentQuestion = false;
    this.clientId = null;
    this._revealDelayMs = 1600;
    this.hostPlayerCount = 0;
  }

  start() {
    this.ws.onMessage((msg) => this.handleMessage(msg));
    this.ws.onClose(() =>
      window.showToast
        ? window.showToast("Socket disconnected", "error")
        : console.error("Disconnected")
    );
    this.ws.connect();

    if (this.mode === "player") {
      this.ui.showConnectedState();
      this.ws.send({ event_type: "PLAYER_JOIN", nickname: this.nickname });
    }

    if (this.mode === "host") {
      const backBtn = document.getElementById("host-back-menu");
      if (backBtn) {
        backBtn.addEventListener("click", () => this.hostExitToMenu());
      }
      const nextBtn = document.getElementById("host-next");
      if (nextBtn) {
        nextBtn.addEventListener("click", () => {
          if (this.currentState === "lobby") {
            this.ws.send({ event_type: "HOST_ACTION", action: "start_question" });
          } else if (
            this.currentState === "question" ||
            this.currentState === "leaderboard"
          ) {
            this.ws.send({ event_type: "HOST_ACTION", action: "next" });
          }
        });
      }
    }
  }

  _updateHostNextLabel() {
    const btn = document.getElementById("host-next");
    if (!btn) return;
    if (this.currentState === "lobby") {
      btn.textContent = "Start Game";
      btn.disabled = this.hostPlayerCount <= 0;
      btn.classList.remove("hidden");
    } else if (this.currentState === "question") {
      btn.textContent = "Show Leaderboard";
      btn.disabled = false;
      btn.classList.remove("hidden");
    } else if (this.currentState === "leaderboard") {
      btn.textContent = "Next Question";
      btn.disabled = false;
      btn.classList.remove("hidden");
    } else if (this.currentState === "finished") {
      btn.textContent = "Game Over";
      btn.disabled = true;
      btn.classList.add("hidden");
    }
  }

  hostExitToMenu() {
    const root = document.getElementById("host-root");
    const pin = root?.dataset?.pin;
    if (pin) {
      fetch(`/api/sessions/${encodeURIComponent(pin)}/close`, { method: "POST" }).catch(() => {});
    }
    sessionStorage.clear();
    localStorage.clear();
    window.location.href = "/host";
  }

  handleMessage(msg) {
    if (msg.event_type === "CONNECTED") {
      this.currentState = "connected";
      this.clientId = msg.client_id || this.clientId;
      if (this.mode === "player") {
        if (this.ui?.setPlayerHeader) this.ui.setPlayerHeader("Connected Successfully");
        this.ui.updateStatus("Waiting for the host to start the game...");
      }
      return;
    }

    if (this.mode === "host") {
      this.handleHostMessage(msg);
      return;
    }

    this.handlePlayerMessage(msg);
  }

  handleHostMessage(msg) {
    if (msg.event_type === "LOBBY_STATE") {
      this.currentState = "lobby";
      this.ui.hostSetView("host-view-lobby");
      const players = (msg.players || []).map((p) => p.nickname || p);
      this.hostPlayerCount = players.length;
      this.ui.setPlayers(players);
      this._updateHostNextLabel();
      return;
    }

    if (msg.event_type === "QUESTION_STATE") {
      this.currentState = "question";
      this.ui.clearReveal("#host-options");
      this.ui.renderHostQuestion({
        questionText: msg.question_text,
        options: msg.options || [],
        imageUrl: msg.image_url,
      });
      this._updateHostNextLabel();
      return;
    }

    if (msg.event_type === "LEADERBOARD_STATE") {
      this.currentState = "leaderboard";
      const idx =
        typeof msg.revealed_correct_index === "number"
          ? msg.revealed_correct_index
          : 0;
      this.ui.revealCorrectAnswer(idx, "#host-options");
      setTimeout(() => {
        this.ui.renderHostLeaderboardTable(msg.leaderboard || []);
        this._updateHostNextLabel();
      }, this._revealDelayMs);
      return;
    }

    if (msg.event_type === "FINISHED_STATE") {
      this.currentState = "finished";
      this.ui.renderHostFinished(msg.leaderboard || []);
      this._updateHostNextLabel();
    }
  }

  handlePlayerMessage(msg) {
    if (msg.event_type === "LOBBY_STATE") {
      this.currentState = "lobby";
      return;
    }

    if (msg.event_type === "QUESTION_STATE") {
      const questionId = msg.question_id ?? `${msg.pin}-${msg.question_index}`;
      const isSameQuestion = this.currentQuestionId === questionId;
      this.currentState = "question";
      const qIndex =
        typeof msg.current_question_index === "number"
          ? msg.current_question_index
          : typeof msg.question_index === "number"
            ? msg.question_index
            : 0;
      if (this.ui?.setPlayerHeader) {
        this.ui.setPlayerHeader(`Question #${qIndex + 1}`);
      }
      if (this.ui?.setTimerMode) this.ui.setTimerMode("question");

      if (!isSameQuestion) {
        this.currentQuestionId = questionId;
        this.answeredCurrentQuestion = false;
        this.ui.clearReveal("#question-options");
        this.ui.hideWaitingOverlay();
        this.ui.transitionStage();
        const secs = msg.question_seconds || 15;
        this.ui.renderQuestion({
          questionText: msg.question_text || "",
          options: msg.options || [],
          onAnswer: (answer) => {
            if (this.answeredCurrentQuestion) return;
            this.answeredCurrentQuestion = true;
            this.ws.send({ event_type: "ANSWER_SUBMITTED", answer });
            this.ui.lockOptions();
            this.ui.showWaitingOverlay();
            this.ui.updateStatus("");
          },
        });
        this.ui.animateTimer(secs);
      }
      this.ui.renderQuestionImage(msg.image_url || null);
      this.ui.updateStatus("");
      return;
    }

    if (msg.event_type === "LEADERBOARD_STATE") {
      this.currentState = "leaderboard";
      this.ui.hideWaitingOverlay();
      this.ui.renderQuestionImage(null);
      if (this.ui?.setTimerMode) this.ui.setTimerMode("leaderboard");
      this.ui.animateTimer(typeof msg.leaderboard_seconds === "number" ? msg.leaderboard_seconds : 10);
      const idx =
        typeof msg.revealed_correct_index === "number"
          ? msg.revealed_correct_index
          : 0;
      this.ui.revealCorrectAnswer(idx, "#question-options");
      this.ui.transitionStage();
      this.ui.renderPlayerLeaderboard?.({
        isCorrect: Boolean(msg.is_correct),
        pointsDelta: Number(msg.points_delta || 0),
        leaderboard: msg.leaderboard || [],
      });
      this.ui.updateStatus("");
      return;
    }

    if (msg.event_type === "FINISHED_STATE") {
      this.currentState = "finished";
      this.ui.hideWaitingOverlay();
      this.ui.renderQuestionImage(null);
      this.ui.updateStatus("");
      const winners = msg.winners || msg.leaderboard || [];
      this.ui.renderPodium(winners);
      this.ui.showGameOver();
    }
  }
}
