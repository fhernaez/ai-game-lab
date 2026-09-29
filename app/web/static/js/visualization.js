(function () {
  const root = document.getElementById("competition-root");
  if (!root) return;
  const competitionId = root.dataset.competitionId;

  const svg = document.getElementById("graph");
  const scoreboardEl = document.getElementById("scoreboard");
  const logEl = document.getElementById("event-log");
  const NS = "http://www.w3.org/2000/svg";

  const nodes = new Map(); // id -> {id, label, role, crewIndex, x, y}
  let scoreboard = {};
  let lastSeq = 0;

  const TEAM_COLORS = ["#38bdf8", "#818cf8"];
  const REFEREE = { id: "referee", x: 400, y: 60, role: "referee", name: "Referee" };

  async function load() {
    const state = await (await fetch(`/api/competitions/${competitionId}/state`)).json();
    buildLayout(state.crews || []);
    renderScoreboard(state.final_state ? state.final_state.scores : null);
    poll();
  }

  async function poll() {
    const data = await (await fetch(`/api/competitions/${competitionId}/events?after=${lastSeq}`)).json();
    const events = data.events || [];
    events.forEach((ev) => { lastSeq = ev.sequence_number; });
    renderBatch(events);
    if (data.status === "queued" || data.status === "running" || data.status === "ready") {
      setTimeout(poll, 1000);
    } else {
      const st = await (await fetch(`/api/competitions/${competitionId}/state`)).json();
      if (st.final_state && st.final_state.scores) {
        scoreboard = st.final_state.scores;
        updateScoreboard();
      }
    }
  }

  function buildLayout(crews) {
    nodes.clear();
    svg.innerHTML = "";
    crews.forEach((crew, ti) => {
      const members = crew.members || [];
      const n = members.length;
      const x = ti === 0 ? 150 : 650;
      members.forEach((m, ai) => {
        const y = 140 + (ai * (360 / Math.max(n - 1, 1)));
        const id = `${crew.name}::${m.role}`;
        nodes.set(id, {
          id,
          label: m.role,
          role: m.role,
          crewIndex: ti,
          crewName: crew.name,
          x,
          y,
        });
      });
    });
    drawNodes();
  }

  function drawNodes() {
    nodes.forEach((node) => drawNode(node, TEAM_COLORS[node.crewIndex]));
    drawNode(REFEREE, "#c084fc");
    nodes.forEach((node) => {
      const line = el("line", {
        x1: node.x, y1: node.y, x2: REFEREE.x, y2: REFEREE.y,
        stroke: "#334155", "stroke-width": 1, "stroke-dasharray": "3 3",
      });
      svg.appendChild(line);
    });
  }

  function drawNode(node, color) {
    const g = el("g");
    const circle = el("circle", {
      cx: node.x, cy: node.y, r: 22, fill: "#0f172a", stroke: color, "stroke-width": 2,
    });
    const text = el("text", {
      x: node.x, y: node.y + 4, "text-anchor": "middle", fill: "#e2e8f0", "font-size": 10,
    });
    text.textContent = node.label;
    const roleText = el("text", {
      x: node.x, y: node.y + 38, "text-anchor": "middle", fill: "#94a3b8", "font-size": 9,
    });
    roleText.textContent = node.role;
    g.appendChild(circle);
    g.appendChild(text);
    g.appendChild(roleText);
    g.dataset.nodeId = node.id;
    svg.appendChild(g);
  }

  function renderScoreboard(scores) {
    scoreboardEl.innerHTML = "";
    const names = Array.from(new Set(Array.from(nodes.values()).map((n) => n.crewName)));
    names.forEach((name) => {
      const div = document.createElement("div");
      div.className = "team";
      div.dataset.team = name;
      div.innerHTML = `<div class="muted">${name}</div><div class="score">0</div>`;
      scoreboardEl.appendChild(div);
    });
    scoreboard = scores || {};
    updateScoreboard();
  }

  function updateScoreboard() {
    Object.entries(scoreboard).forEach(([name, value]) => {
      const el = scoreboardEl.querySelector(`[data-team="${name}"] .score`);
      if (el) el.textContent = value;
    });
  }

  function logEvent(ev) {
    const item = document.createElement("div");
    item.className = "item";
    const p = ev.payload || {};
    let detail = "";
    if (ev.event_type === "CREW_MESSAGE") {
      detail = (p.parsed && p.parsed.message) || p.raw || "";
    } else if (ev.event_type === "ACTION_PROPOSED") {
      detail = (p.action && p.action.action) || "";
    } else if (ev.event_type === "REFEREE_VERDICT") {
      const v = p.verdict || {};
      detail = `accepted=${v.accepted}, score=${v.score} — ${v.explanation || ""}`;
    } else if (ev.event_type === "SCORE_CHANGED") {
      detail = `${p.crew} +${p.delta} (${p.explanation || ""})`;
    } else if (ev.event_type === "ROUND_STARTED" || ev.event_type === "ROUND_FINISHED") {
      detail = `round ${p.round || ""}`;
    }
    item.innerHTML = `<span class="etype">${ev.event_type}</span> <span class="muted">${ev.actor_id || ""} ${p.crew || ""}</span><br>${detail}`;
    logEl.prepend(item);
    while (logEl.children.length > 100) logEl.removeChild(logEl.lastChild);
  }

  function renderBatch(events) {
    let i = 0;
    const step = () => {
      if (i >= events.length) return;
      const ev = events[i];
      renderEvent(ev);
      logEvent(ev);
      i += 1;
      setTimeout(step, 120);
    };
    step();
  }

  function renderEvent(ev) {
    const p = ev.payload || {};

    if (ev.event_type === "CREW_MESSAGE") {
      const node = nodes.get(`${p.crew}::${ev.actor_id}`);
      if (node) pulse(node);
    } else if (ev.event_type === "ACTION_PROPOSED") {
      const node = nodes.get(`${p.crew}::${ev.actor_id}`);
      if (node) edge(node, REFEREE, "#38bdf8");
    } else if (ev.event_type === "REFEREE_VERDICT") {
      pulse(REFEREE);
      const v = p.verdict || {};
      const color = v.accepted ? "#34d399" : "#f87171";
      const target = Array.from(nodes.values()).find((n) => n.crewName === p.crew);
      if (target) edge(REFEREE, target, color);
    } else if (ev.event_type === "SCORE_CHANGED" || ev.event_type === "STATE_CHANGED") {
      if (p.state && p.state.scores) scoreboard = p.state.scores;
      updateScoreboard();
    }
  }

  function pulse(node) {
    const c = el("circle", { cx: node.x, cy: node.y, r: 22, fill: "none", stroke: "#e2e8f0", "stroke-width": 2 });
    svg.appendChild(c);
    animateAttr(c, "r", 22, 40, 600, () => c.remove());
  }

  function edge(a, b, color) {
    const line = el("line", {
      x1: a.x, y1: a.y, x2: b.x, y2: b.y,
      stroke: color, "stroke-width": 3,
    });
    svg.appendChild(line);
    setTimeout(() => line.remove(), 1200);
  }

  function animateAttr(element, attr, from, to, duration, done) {
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      element.setAttribute(attr, from + (to - from) * t);
      if (t < 1) requestAnimationFrame(tick);
      else if (done) done();
    };
    requestAnimationFrame(tick);
  }

  function el(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    return node;
  }

  load();
})();
