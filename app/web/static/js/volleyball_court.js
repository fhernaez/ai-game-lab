/*
 * volleyball_court.js — independent graphical match simulation module.
 *
 * Renders the beach-volleyball court, the four players, and the ball, driven only
 * by the event stream from /api/matches/<id>/events and /state. It is self-contained
 * so it can be replaced or upgraded without touching the rest of the app.
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
  const COURT_W = 8, COURT_H = 16, NET_Y = 8;
  const PAD = 20, W = 800, H = 420;

  const TEAM_COLORS = ["#38bdf8", "#fbbf24"];
  let players = [];   // {id, team, x, y, el}
  let ballEl = null;
  let lastSeq = 0;
  let scoreboard = {};

  function sx(x) { return PAD + (x / COURT_W) * (H - PAD * 2); }
  function sy(y) { return (y / COURT_H) * W; }

  async function load() {
    const state = await (await fetch(`/api/matches/${matchId}/state`)).json();
    buildCourt(state.teams || []);
    renderScoreboard(state.final_state);
    poll();
  }

  function buildCourt(teams) {
    svg.innerHTML = "";
    // sand
    svg.appendChild(rect(0, 0, W, H, "#b45309"));
    // halves
    svg.appendChild(rect(sy(0), sx(0), W / 2, H - PAD * 2, "#c2701a"));
    svg.appendChild(rect(sy(NET_Y), sx(0), W / 2, H - PAD * 2, "#c2701a"));
    // net line
    svg.appendChild(line(sy(NET_Y), sx(0), sy(NET_Y), sx(COURT_W), "#e2e8f0", 3));
    // side/end lines
    svg.appendChild(rect(sy(0), sx(0), W, H - PAD * 2, "none", "#e2e8f0", 2));

    players = [];
    teams.forEach((team, ti) => {
      const positions = ti === 0 ? [[2, 3], [6, 5]] : [[2, 11], [6, 13]];
      (team.players || []).forEach((p, pi) => {
        const pos = positions[pi % positions.length];
        const id = `${team.name}::${p.slot}`;
        const el = circle(sx(pos[0]), sy(pos[1]), 12, TEAM_COLORS[ti]);
        const label = text(sx(pos[0]), sy(pos[1]) + 4, p.name || `P${p.slot}`);
        svg.appendChild(el);
        svg.appendChild(label);
        players.push({ id, team: ti, teamName: team.name, slot: p.slot, x: pos[0], y: pos[1], el, label });
      });
    });
    ballEl = circle(sx(4), sy(0), 6, "#ffffff");
    svg.appendChild(ballEl);
  }

  function renderScoreboard(finalState) {
    scoreboardEl.innerHTML = "";
    const names = players.length ? Array.from(new Set(players.map(p => p.teamName))) : [];
    names.forEach((name) => {
      const div = document.createElement("div");
      div.className = "team";
      div.dataset.team = name;
      div.innerHTML = `<div class="muted">${name}</div><div class="score">0 - 0</div>`;
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

  function movePlayer(player, x, y) {
    player.el.setAttribute("cx", sx(x));
    player.el.setAttribute("cy", sy(y));
    player.label.setAttribute("x", sx(x));
    player.label.setAttribute("y", sy(y) + 4);
    player.x = x; player.y = y;
  }

  function moveBall(x, y) {
    ballEl.setAttribute("cx", sx(x));
    ballEl.setAttribute("cy", sy(y));
  }

  function logEvent(ev) {
    const item = document.createElement("div");
    item.className = "item";
    const p = ev.payload || {};
    let detail = "";
    if (ev.event_type === "DECISION") {
      const d = p.parsed || {};
      detail = `${p.action_hint} → ${d.action} power=${(d.power ?? '').toFixed(2)} target=[${(d.target || []).join(', ')}] model=${p.model || ''}`;
    } else if (ev.event_type === "TOUCH") {
      detail = `${p.action || ''} ball=(${(p.ball?.x ?? 0).toFixed(1)}, ${(p.ball?.y ?? 0).toFixed(1)})`;
    } else if (ev.event_type === "POINT") {
      detail = `team ${p.team} scores (${p.reason || ''})`;
    } else if (ev.event_type === "SET_WON" || ev.event_type === "MATCH_FINISHED") {
      detail = ev.event_type;
    }
    item.innerHTML = `<span class="etype">${ev.event_type}</span> <span class="muted">${ev.actor_id || ''} team ${p.team ?? ''}</span><br>${detail}`;
    logEl.prepend(item);
    while (logEl.children.length > 120) logEl.removeChild(logEl.lastChild);
  }

  function renderEvent(ev) {
    const p = ev.payload || {};
    if (ev.event_type === "DECISION") {
      const actor = players.find(pl => pl.teamName === p.team_name && pl.slot === p.slot);
      if (actor && p.parsed && p.parsed.target) {
        movePlayer(actor, actor.x, actor.y);
        pulse(actor.el);
      }
    } else if (ev.event_type === "TOUCH" && p.ball) {
      moveBall(p.ball.x, p.ball.y);
      const team = p.team;
      const actor = players.find(pl => pl.team === team);
      if (actor) movePlayer(actor, p.ball.x, p.ball.y);
    } else if (ev.event_type === "POINT" && p.payload) {
      scoreboard = p.payload;
      updateScoreboard();
    } else if (ev.event_type === "SET_WON" && p.payload) {
      scoreboard = p.payload;
      updateScoreboard();
    } else if (ev.event_type === "MATCH_FINISHED" && p.payload) {
      scoreboard = p.payload;
      updateScoreboard();
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
      setTimeout(step, 140);
    };
    step();
  }

  async function finalize() {
    const st = await (await fetch(`/api/matches/${matchId}/state`)).json();
    if (st.final_state) { scoreboard = st.final_state; updateScoreboard(); }
  }

  function pulse(el) {
    const r = el.getAttribute("r");
    el.setAttribute("r", Number(r) + 4);
    setTimeout(() => el.setAttribute("r", r), 400);
  }

  function rect(x, y, w, h, fill, stroke, sw) {
    return el("rect", { x, y, width: w, height: h, fill, stroke: stroke || "none", "stroke-width": sw || 0 });
  }
  function line(x1, y1, x2, y2, stroke, sw) {
    return el("line", { x1, y1, x2, y2, stroke, "stroke-width": sw });
  }
  function circle(cx, cy, r, fill) {
    return el("circle", { cx, cy, r, fill, stroke: "#0f172a", "stroke-width": 1.5 });
  }
  function text(x, y, s) {
    const t = el("text", { x, y, "text-anchor": "middle", fill: "#0f172a", "font-size": 11, "font-weight": 700 });
    t.textContent = s;
    return t;
  }
  function el(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  }

  load();
})();
