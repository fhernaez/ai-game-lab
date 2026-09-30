/*
 * volleyball_court.js — independent graphical match simulation module.
 *
 * Renders the beach-volleyball court, the four players, and the ball, driven only
 * by the event stream from /api/matches/<id>/events and /state. Self-contained so it
 * can be replaced or upgraded without touching the rest of the app.
 *
 * Players move smoothly to the `move_to` destination from each DECISION (constant
 * size); the ball flies along each TRAJECTORY and is drawn larger when high.
 */
(function () {
  const root = document.getElementById("match-root");
  if (!root) return;
  const matchId = root.dataset.matchId;

  const svg = document.getElementById("court-svg");
  const scoreboardEl = document.getElementById("scoreboard");
  const logEl = document.getElementById("event-log");
  const statusEl = document.getElementById("match-status");
  const NS = "http://www.w3.org/2000/svg";

  // Court mapping: X (width 0..8) -> vertical, Y (length 0..16) -> horizontal.
  // Horizontal margins leave room to show the server behind the end line.
  const COURT_W = 8, COURT_H = 16, NET_Y = 8;
  const W = 880, H = 460, PAD_Y = 24, MARGIN_X = 60, COURT_PX = 720;
  const ARC_SCALE = 26;

  const TEAM_COLORS = ["#38bdf8", "#fbbf24"];
  let players = [];
  let ballEl = null;
  let lastSeq = 0;
  let scoreboard = {};
  let ballToken = 0;

  const sx = (x) => PAD_Y + (x / COURT_W) * (H - PAD_Y * 2);
  const sy = (y) => MARGIN_X + (y / COURT_H) * COURT_PX;

  async function load() {
    const state = await (await fetch(`/api/matches/${matchId}/state`)).json();
    buildCourt(state.teams || []);
    renderScoreboard(state.final_state);
    setStatus(state.status);
    poll();
  }

  function setStatus(status) {
    if (!statusEl) return;
    if (status === "queued" || status === "accepted" || status === "ready") {
      statusEl.textContent = "Waiting to start…";
    } else if (status === "running") {
      statusEl.textContent = "▶ Match running…";
    } else if (status === "finished" && scoreboard && scoreboard.winner !== undefined) {
      const names = Array.from(new Set(players.map(p => p.teamName)));
      statusEl.textContent = "Finished — " + (names[scoreboard.winner] || "winner");
    } else if (status === "failed" || status === "cancelled") {
      statusEl.textContent = "Match " + status + ".";
    } else {
      statusEl.textContent = "";
    }
  }

  function buildCourt(teams) {
    svg.innerHTML = "";
    svg.appendChild(el("rect", { x: 0, y: 0, width: W, height: H, fill: "#0f172a" }));
    // Sand (with outside space around the court).
    svg.appendChild(el("rect", { x: sy(0), y: sx(0), width: COURT_PX, height: H - PAD_Y * 2, fill: "#f59e0b" }));
    // Court lines.
    svg.appendChild(el("rect", { x: sy(0), y: sx(0), width: COURT_PX, height: H - PAD_Y * 2, fill: "none", stroke: "#fef3c7", "stroke-width": 2 }));
    // Net band.
    svg.appendChild(el("rect", { x: sy(NET_Y) - 2, y: sx(0), width: 4, height: H - PAD_Y * 2, fill: "#e2e8f0" }));

    players = [];
    teams.forEach((team, ti) => {
      const tag = ti === 0 ? "A" : "B";
      const positions = ti === 0 ? [[2, 3], [6, 5]] : [[2, 11], [6, 13]];
      const nameX = ti === 0 ? sy(3) : sy(13);
      const nameEl = el("text", { x: nameX, y: 16, "text-anchor": "middle", fill: "#fef3c7", "font-size": 13, "font-weight": 700 });
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
        players.push({ id: `${team.name}::${p.slot}`, team: ti, teamName: team.name, slot: p.slot, x: pt[0], y: pt[1], el: c, label: lb, animToken: 0 });
      });
    });
    ballEl = el("circle", { cx: sy(8), cy: sx(4), r: 4, fill: "#ffffff", stroke: "#0f172a", "stroke-width": 1.5 });
    svg.appendChild(ballEl);
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

  function setPlayerPos(player, x, y) {
    player.x = x; player.y = y;
    player.el.setAttribute("cx", sy(y));
    player.el.setAttribute("cy", sx(x));
    player.label.setAttribute("x", sy(y));
    player.label.setAttribute("y", sx(x) + 4);
  }

  function animatePlayer(player, tx, ty, speed) {
    const fromX = player.x, fromY = player.y;
    const dur = Math.max(250, Math.min(1800, 900 / (speed || 0.5)));
    const token = ++player.animToken;
    const start = performance.now();
    function step(now) {
      if (token !== player.animToken) return;
      const t = Math.min(1, (now - start) / dur);
      setPlayerPos(player, fromX + (tx - fromX) * t, fromY + (ty - fromY) * t);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function setBall(x, y, z) {
    ballEl.setAttribute("cx", sy(y));
    ballEl.setAttribute("cy", sx(x) - (z || 0) * ARC_SCALE);
    ballEl.setAttribute("r", 4 + (z || 0) * 2.5);
  }

  function animateBall(from, to, dur) {
    const token = ++ballToken;
    const start = performance.now();
    const peak = Math.max(1.5, (from.z || 0) + (to.z || 0) + 1.0);
    function step(now) {
      if (token !== ballToken) return;
      const t = Math.min(1, (now - start) / dur);
      const x = from.x + (to.x - from.x) * t;
      const y = from.y + (to.y - from.y) * t;
      const z = Math.sin(Math.PI * t) * peak;
      setBall(x, y, z);
      if (t < 1) requestAnimationFrame(step);
      else setBall(to.x, to.y, 0);
    }
    requestAnimationFrame(step);
  }

  function logEvent(ev) {
    const item = document.createElement("div");
    item.className = "item";
    const p = ev.payload || {};
    let detail = "";
    if (ev.event_type === "DECISION") {
      const d = p.parsed || {};
      detail = `${p.message || ''} <span class="muted">(${d.action} power=${Number(d.power || 0).toFixed(2)} → target [${(d.target || []).map(v => Number(v).toFixed(1)).join(', ')}] · move to [${(d.move_to || []).map(v => Number(v).toFixed(1)).join(', ')}])</span>`;
      if (p.error) detail += `<br><span class="etype">⚠ ${p.error}</span>`;
    } else if (ev.event_type === "TRAJECTORY") {
      const to = p.ball || {};
      detail = `ball → (${(to.x ?? 0).toFixed(1)}, ${(to.y ?? 0).toFixed(1)}) · ${p.flight_time}s · offset ${p.offset}`;
    } else if (ev.event_type === "INTERCEPT") {
      detail = `slot ${p.slot} reaches the ball in ${p.time}s`;
    } else if (ev.event_type === "POINT") {
      detail = `team ${p.team} scores (${p.reason || ''})`;
    } else if (ev.event_type === "SET_WON" || ev.event_type === "MATCH_FINISHED") {
      detail = ev.event_type;
    }
    item.innerHTML = `<span class="etype">${ev.event_type}</span> <span class="muted">${ev.actor_id || ''}${p.team_name ? ' · ' + p.team_name : ''}</span><br>${detail}`;
    logEl.prepend(item);
    while (logEl.children.length > 150) logEl.removeChild(logEl.lastChild);
  }

  function renderEvent(ev) {
    const p = ev.payload || {};
    if (ev.event_type === "DECISION") {
      const actor = findPlayer(p.team_name, p.slot);
      if (actor) {
        if (p.from_pos) setPlayerPos(actor, p.from_pos[0], p.from_pos[1]);
        const to = p.move_to || (p.parsed && p.parsed.move_to) || [actor.x, actor.y];
        animatePlayer(actor, to[0], to[1], p.move_speed || (p.parsed && p.parsed.move_speed) || 0.5);
      }
    } else if (ev.event_type === "TRAJECTORY") {
      const from = p.from_ball || { x: 4, y: 8, z: 0 };
      const to = p.ball || from;
      const dur = Math.max(350, Math.min(2200, (p.flight_time || 0.5) * 900));
      animateBall(from, to, dur);
    } else if (ev.event_type === "INTERCEPT") {
      const actor = findPlayer(p.team_name, p.slot);
      if (actor && p.at) animatePlayer(actor, p.at[0], p.at[1], 0.7);
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
      setTimeout(step, 60);
    };
    step();
  }

  async function finalize() {
    const st = await (await fetch(`/api/matches/${matchId}/state`)).json();
    if (st.final_state) { scoreboard = st.final_state; updateScoreboard(); }
    setStatus(st.status);
  }

  function el(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  }

  load();
})();
