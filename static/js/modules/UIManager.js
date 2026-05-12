export class UIManager {
  constructor({ mode }) {
    this.mode = mode;
  }

  setPlayerHeader(text) {
    const h = document.getElementById("player-header");
    if (h) h.textContent = text;
  }

  setTimerMode(mode) {
    const bar = document.getElementById("timer-bar");
    if (!bar) return;
    bar.classList.toggle("timer-leaderboard", mode === "leaderboard");
  }

  showConnectedState() {
    const join = document.getElementById("join-panel");
    const game = document.getElementById("game-panel");
    if (join) join.classList.add("hidden");
    if (game) game.classList.remove("hidden");
  }

  updateStatus(text) {
    const status = document.getElementById("status-text");
    if (status) status.textContent = text;
  }

  showGameOver() {
    const gameOver = document.getElementById("game-over");
    if (gameOver) gameOver.classList.remove("hidden");
  }

  renderQuestionImage(imageUrl) {
    const wrap = document.getElementById("question-media");
    const img = document.getElementById("question-image");
    if (!wrap || !img) return;
    if (imageUrl) {
      img.src = imageUrl;
      wrap.classList.remove("hidden");
    } else {
      img.removeAttribute("src");
      wrap.classList.add("hidden");
    }
  }

  transitionStage() {
    const stage = document.getElementById("state-stage");
    if (!stage) return;
    stage.classList.remove("state-pop");
    stage.offsetHeight;
    stage.classList.add("state-pop");
  }

  clearReveal(rootSelector = "#question-options") {
    const root = document.querySelector(rootSelector);
    if (!root) return;
    root.querySelectorAll("[data-opt-index]").forEach((el) => {
      el.classList.remove("correct-flash", "dimmed");
    });
  }

  revealCorrectAnswer(correctIndex, rootSelector = "#question-options") {
    const root = document.querySelector(rootSelector);
    if (!root) return;
    root.querySelectorAll("[data-opt-index]").forEach((el) => {
      const idx = Number(el.getAttribute("data-opt-index"));
      el.classList.remove("correct-flash", "dimmed");
      if (idx === correctIndex) el.classList.add("correct-flash");
      else el.classList.add("dimmed");
    });
  }

  renderQuestion({ questionText, options, onAnswer }) {
    const q = document.getElementById("question-text");
    const grid = document.getElementById("question-options");
    const lb = document.getElementById("leaderboard-self");
    if (!q || !grid) return;
    this.clearReveal("#question-options");
    this.hideWaitingOverlay();
    if (lb) lb.classList.add("hidden");
    q.classList.remove("hidden");
    grid.classList.remove("hidden");
    q.textContent = questionText || "Question";
    grid.innerHTML = "";
    const cleaned = (options || [])
      .slice(0, 4)
      .map((o) => (o == null ? "" : String(o)).trim())
      .filter((o) => o.length > 0);
    cleaned.forEach((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `option-btn opt-${index}`;
      button.setAttribute("data-opt-index", String(index));
      button.textContent = option;
      button.addEventListener("click", () => onAnswer(index));
      if (cleaned.length % 2 === 1 && index === cleaned.length - 1 && cleaned.length > 1) {
        button.classList.add("span-2");
      }
      grid.appendChild(button);
    });
  }

  lockOptions() {
    const grid = document.getElementById("question-options");
    if (!grid) return;
    grid.querySelectorAll("button.option-btn").forEach((btn) => {
      btn.disabled = true;
      btn.classList.add("disabled");
    });
  }

  showWaitingOverlay() {
    const overlay = document.getElementById("answer-wait-overlay");
    if (overlay) overlay.classList.remove("hidden");
  }

  hideWaitingOverlay() {
    const overlay = document.getElementById("answer-wait-overlay");
    if (overlay) overlay.classList.add("hidden");
  }

  renderPlayerResult(isCorrect) {
    const lb = document.getElementById("leaderboard-self");
    const q = document.getElementById("question-text");
    const grid = document.getElementById("question-options");
    if (!lb) return;
    if (q) q.classList.add("hidden");
    if (grid) grid.classList.add("hidden");
    lb.classList.remove("hidden");
    lb.classList.remove("result-correct", "result-incorrect");
    lb.classList.add(isCorrect ? "result-correct" : "result-incorrect");
    lb.textContent = isCorrect ? "Correct! Great timing." : "Incorrect. Next one!";
  }

  renderPlayerLeaderboard({ isCorrect, pointsDelta, leaderboard }) {
    const lb = document.getElementById("leaderboard-self");
    const q = document.getElementById("question-text");
    const grid = document.getElementById("question-options");
    if (!lb) return;
    if (q) q.classList.add("hidden");
    if (grid) grid.classList.add("hidden");
    lb.classList.remove("hidden");
    lb.classList.remove("result-correct", "result-incorrect");
    lb.classList.add(isCorrect ? "result-correct" : "result-incorrect");

    const msg = isCorrect
      ? `CORRECT! +${Number(pointsDelta || 0)}`
      : "INCORRECT. Next time!";

    const top = Array.isArray(leaderboard) ? leaderboard.slice(0, 10) : [];
    const rows = top
      .map(
        (r, idx) =>
          `<tr><td>${idx + 1}</td><td>${escapeHtml(r.nickname)}</td><td class="lb-score">${r.score}</td></tr>`
      )
      .join("");

    lb.innerHTML = `
      <div class="feedback ${isCorrect ? "feedback-correct" : "feedback-incorrect"}">${msg}</div>
      <div class="lb-title">Leaderboard</div>
      <table class="lb-table">
        <thead><tr><th>#</th><th>Nickname</th><th>Score</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  renderPodium(leaderboard, containerId = "podium") {
    const wrap = document.getElementById(containerId);
    if (!wrap || !Array.isArray(leaderboard)) return;
    const top = leaderboard.slice(0, 3);
    const [first, second, third] = [top[0], top[1], top[2]];
    const slot = (data, medal) => {
      if (!data) {
        return `<div class="podium-slot ${medal}"><div class="podium-icon">—</div><div class="podium-name">—</div><div class="podium-score">—</div><div class="podium-block"></div></div>`;
      }
      const icon = medal === "gold" ? "🥇" : medal === "silver" ? "🥈" : "🥉";
      return `<div class="podium-slot ${medal}">
        <div class="podium-icon">${icon}</div>
        <div class="podium-name">${escapeHtml(data.nickname)}</div>
        <div class="podium-score">${data.score}</div>
        <div class="podium-block"></div>
      </div>`;
    };
    wrap.innerHTML = `<div class="podium-container"><div class="podium-row">${slot(second, "silver")}${slot(first, "gold")}${slot(third, "bronze")}</div></div>`;
  }

  setPlayers(players) {
    const ul = document.getElementById("player-list");
    if (!ul) return;
    ul.innerHTML = "";
    players.forEach((p) => {
      const name = typeof p === "string" ? p : p.nickname;
      const li = document.createElement("li");
      li.textContent = name;
      ul.appendChild(li);
    });
  }

  animateTimer(seconds) {
    const bar = document.getElementById("timer-bar");
    if (!bar) return;
    bar.style.animation = "none";
    bar.offsetHeight;
    bar.style.animation = `timer-shrink ${Math.max(0.1, seconds)}s linear forwards`;
  }

  hostSetView(view) {
    ["host-view-lobby", "host-view-question", "host-view-leaderboard", "host-view-finished"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.add("hidden");
    });
    const show = document.getElementById(view);
    if (show) show.classList.remove("hidden");
  }

  renderHostQuestion({ questionText, options, imageUrl }) {
    const qt = document.getElementById("host-q-text");
    const grid = document.getElementById("host-options");
    const imgWrap = document.getElementById("host-q-image-wrap");
    const img = document.getElementById("host-q-image");
    if (qt) qt.textContent = questionText || "";
    if (grid) {
      this.clearReveal("#host-options");
      grid.innerHTML = "";
      const cleaned = (options || [])
        .slice(0, 4)
        .map((o) => (o == null ? "" : String(o)).trim())
        .filter((o) => o.length > 0);
      cleaned.forEach((text, index) => {
        const block = document.createElement("div");
        block.className = `kahoot-block opt-${index}`;
        block.setAttribute("data-opt-index", String(index));
        block.textContent = text;
        if (cleaned.length % 2 === 1 && index === cleaned.length - 1 && cleaned.length > 1) {
          block.classList.add("span-2");
        }
        grid.appendChild(block);
      });
    }
    if (imgWrap && img) {
      if (imageUrl) {
        img.src = imageUrl;
        imgWrap.classList.remove("hidden");
      } else {
        img.removeAttribute("src");
        imgWrap.classList.add("hidden");
      }
    }
    this.hostSetView("host-view-question");
  }

  renderHostLeaderboardTable(rows) {
    const body = document.getElementById("host-lb-body");
    if (!body) return;
    body.innerHTML = (rows || [])
      .map(
        (r) =>
          `<tr><td>${escapeHtml(r.nickname)}</td><td class="lb-score">${r.score}</td></tr>`
      )
      .join("");
    this.hostSetView("host-view-leaderboard");
  }

  renderHostFinished(leaderboard) {
    const pid = document.getElementById("podium-host") ? "podium-host" : "podium";
    this.renderPodium(leaderboard, pid);
    this.hostSetView("host-view-finished");
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
