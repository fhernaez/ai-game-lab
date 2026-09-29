/*
 * volleyball_court.js — independent graphical match simulation module.
 *
 * Renders the beach-volleyball court, the four players, and the ball, driven only
 * by the event stream from /api/matches/<id>/events and /state. Self-contained so it
 * can be replaced or upgraded without touching the rest of the app.
 */
(function () {
  const root = document.getElementById("match-root");
  if (!root) return;
  const matchId = root.dataset.matchId;

  const svg = document.getElementById("court-svg");
  const scoreboardEl = document.getElementById("scoreboard");
  const logEl = document.getElementById("event-log");
  const NS = "http://www.w3.org/2000/svg";

  // Court mapping: X (width 0..8) -> vertical, Y (length 0..16) -> horizontal.
  const COURT_W = 8, COURT_H = 16, NET_Y = 8, NET_H = 2.43;
  const PAD = 24, W = 800, H = 440;
  const ARC_SCALE = 26;   // pseudo-3D height pixels per meter of z

  const TEAM_COLORS = ["#38bdf8", "#fbbf24"];
  let players = [];
  let ballEl = null;
  let lastSeq = 0;
  let scoreboard = {};
  let animToken = 0;

  const sx = (x) => PAD + (x / COURT_W) * (H - PAD * 2);
  const sy = (y) => (y / COURT_H) * W;
  const pos = (x, y, z) => ({ cx: sy(y), cy: sx(x) - (z || 0) * ARC_SCALE });

  async function load() {
    const state = await (await fetch(`/api/matches/${matchId}/state`)).json();
    buildCourt(state.teams || []);
    renderScoreboard(state.final_state);
    poll();
  }

  function buildCourt(teams) {
    svg.innerHTML = "";
    // Sand.
    svg.appendChild(el("rect", { x: 0, y: 0, width: W, height: H, fill: "#d97706" }));
    // Court surface.
    svg.appendChild(el("rect", { x: 0, y: PAD, width: W, height: H - PAD * 2, fill: "#f59e0b" }));
    // Side / end lines.
    svg.appendChild(el("rect", { x: 1, y: PAD, width: W - 2, height: H - PAD * 2, fill: "none", stroke: "#fef3c7", "stroke-width": 2 }));
    // Net band (posts + line).
    svg.appendChild(el("rect", { x: sy(NET_Y) - 2, y: PAD, width: 4, height: H - PAD * 2, fill: "#e2e8f0" }));
    svg.appendChild(el("text", { x: sy(NET_Y), y: 14, "text-anchor": "middle", fill: "#78350f", "font-size": 12, "font-weight": 700, transform: `rotate(90 ${sy(NET_Y)} 14)` }));
    const netLabel = svg.lastChild; netLabel.textContent = "NET";

    players = [];
    teams.forEach((team, ti) => {
      const tag = ti === 0 ? "A" : "B";
      const positions = ti === 0 ? [[2, 3], [6, 5]] : [[2, 11], [6, 13]];
      const nameX = ti === 0 ? 130 : 670;
      const nameEl = el("text", { x: nameX, y: 26, "text-anchor": "middle", fill: "#78350f", "font-size": 13, "font-weight": 700 });
      nameEl.textContent = team.name || `Team ${tag}`;
      svg.appendChild(nameEl);
      (team.players || []).forEach((p, pi) => {
        const pt = positions[pi % positions.length];
        const g = el("g");
        const c = el("circle", { cx: sy(pt[1]), cy: sx(pt[0]), r: 13, fill: TEAM_COLORS[ti], stroke: "#0f172a", "stroke-width": 2 });
        const lb = el("text", { x: sy(pt[1]), y: sx(pt[0]) + 4, "text-anchor": "middle", fill: "#0f172a", "font-size": 11, "font-weight": 800 });
        lb.textContent = `${tag}${p.slot}`;
        g.appendChild(c); g.appendChild(lb);
        svg.appendChild(g);
        players.push({ id: `${team.name}::${p.slot}`, team: ti, teamName: team.name, slot: p.slot, x: pt[0], y: pt[1], el: c, label: lb });
      });
    });
    ballEl = el("circle", { r: 6, fill: "#ffffff", stroke: "#0f172a", "stroke-width": 1.5 });
    svg.appendChild(ballEl);
    const bp = pos(4, 0, 0);
    ballEl.setAttribute("cx", bp.cx); ballEl.setAttribute("cy", bp.cy);
  }

  function renderScoreboard(finalState) {
    scoreboardEl.innerHTML = "";
    const names = Array.from(new Set(players.map(p => p.teamName)));
    names.forEach((name) => {
      const div = document.createElement("div");
      div.className = "team"; div.dataset.team = name;
      div.innerHTML = `<div class="muted">${name}</div><div class="score">sets 0 · 0</div>`;
      scoreboardEl.appendChild(div);
    });
    scoreboard = finalState || {};
    updateScoreboard();
  }

  function updateScoreboard() {
    const names = Array.from(new Set(players.map(p => p.teamName)));
    if (!scoreboard || !scoreboard.set_points) return;
    names.forEach((name, i) => {
      const el = scoreboardEl.querySelector(`[data-team="${name}"] .score`);
      if (el) {
        const pts = scoreboard.set_points ? scoreboard.set_points[i] : 0;
        const sets = scoreboard.sets_won ? scoreboard.sets_won[i] : 0;
        el.textContent = `sets ${sets} · ${pts}`;
      }
    });
  }

  function findPlayer(teamName, slot) {
    return players.find(p => p.teamName === teamName && p.slot === slot);
  }

  function setBall(x, y, z) {
    const bp = pos(x, y, z || 0);
    ballEl.setAttribute("cx", bp.cx);
    ballEl.setAttribute("cy", bp.cy);
  }

  function movePlayer(player, x, y) {
    player.el.setAttribute("cx", sy(y));
    player.el.setAttribute("cy", sx(x));
    player.label.setAttribute("x", sy(y));
    player.label.setAttribute("y", sx(x) + 4);
    player.x = x; player.y = y;
  }

  function animateBall(from, to, dur) {
    const token = ++animToken;
    const start = performance.now();
    const fromPos = pos(from.x, from.y, from.z || 0);
    const toPos = pos(to.x, to.y, to.z || 0);
    const peak = Math.max(2.0, (from.z || 0) + (to.z || 0) + 1.2);

    function tick(now) {
      if (token !== animToken) return;
      const t = Math.min(1, (now - start) / (dur || 600));
      const cx = fromPos.cx + (toPos.cx - fromPos.cx) * t;
      const cy = fromPos.cy + (toPos.cy - fromPos.cy) * t;
      // Parabolic height for a pseudo-3D arc.
      const z = Math.sin(Math.PI * t) * peak;
      ballEl.setAttribute("cx", cx);
      ballEl.setAttribute("cy", cy - z * ARC_SCALE);
      if (t < 1) requestAnimationFrame(tick);
      else { ballEl.setAttribute("cx", toPos.cx); ballEl.setAttribute("cy", toPos.cy); }
    }
    requestAnimationFrame(tick);
  }

  function pulse(el) {
    const r = el.getAttribute("r");
    el.setAttribute("r", Number(r) + 5);
    setTimeout(() => el.setAttribute("r", r), 350);
  }

  function logEvent(ev) {
    const item = document.createElement("div");
    item.className = "item";
    const p = ev.payload || {};
    let detail = "";
    if (ev.event_type === "DECISION") {
      const d = p.parsed || {};
      detail = `${p.action_hint} → ${d.action} power=${Number(d.power || 0).toFixed(2)} target=[${(d.target || []).map(v => Number(v).toFixed(1)).join(', ')}] model=${p.model || ''}`;
    } else if (ev.event_type === "TOUCH") {
      detail = `${p.action || ''} → (${(p.ball?.x ?? 0).toFixed(1)}, ${(p.ball?.y ?? 0).toFixed(1)})${p.fault ? ` FAULT(${p.fault})` : ''}`;
    } else if (ev.event_type === "POINT") {
      detail = `team ${p.team} scores (${p.reason || ''})`;
    } else if (ev.event_type === "SET_WON" || ev.event_type === "MATCH_FINISHED") {
      detail = ev.event_type;
    }
    item.innerHTML = `<span class="etype">${ev.event_type}</span> <span class="muted">${ev.actor_id || ''}</span><br>${detail}`;
    logEl.prepend(item);
    while (logEl.children.length > 150) logEl.removeChild(logEl.lastChild);
  }

  function renderEvent(ev) {
    const p = ev.payload || {};
    if (ev.event_type === "DECISION") {
      const actor = findPlayer(p.team_name, p.slot);
      if (actor) pulse(actor.el);
    } else if (ev.event_type === "TOUCH") {
      const actor = findPlayer(p.team_name, p.slot);
      const from = p.from_ball || { x: 4, y: 8, z: 0 };
      const to = p.ball || from;
      if (actor) movePlayer(actor, to.x, to.y);
      animateBall(from, to, 550);
    } else if (ev.event_type === "POINT" && p.payload) {
      scoreboard = p.payload; updateScoreboard();
    } else if (ev.event_type === "SET_WON" && p.payload) {
      scoreboard = p.payload; updateScoreboard();
    } else if (ev.event_type === "MATCH_FINISHED" && p.payload) {
      scoreboard = p.payload; updateScoreboard();
    }
  }

  async function poll() {
    const data = await (await fetch(`/api/matches/${matchId}/events?after=${lastSeq}`)).json();
    const events = data.events || [];
    events.forEach((ev) => { lastSeq = ev.sequence_number; });
    let i = 0;
    const step = () => {
      if (i >= events.length) {
        if (data.status === "queued" || data.status === "running") setTimeout(poll, 900);
        else finalize();
        return;
      }
      const ev = events[i];
      renderEvent(ev);
      logEvent(ev);
      i += 1;
      setTimeout(step, 220);
    };
    step();
  }

  async function finalize() {
    const st = await (await fetch(`/api/matches/${matchId}/state`)).json();
    if (st.final_state) { scoreboard = st.final_state; updateScoreboard(); }
  }

  function el(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  }

  load();
})();
