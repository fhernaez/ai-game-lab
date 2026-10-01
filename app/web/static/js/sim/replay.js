/*
 * replay.js — deterministic event-log → timeline engine.
 *
 * Compiles the event stream into animation segments with cumulative start times,
 * then renders any point in time by replaying segments up to t. This gives
 * play / pause / seek / speed with a single applyProgress(t) method.
 */

const FLIGHT_SCALE = 450;
const MOVE_DUR = (speed) => Math.max(120, Math.min(900, 400 / (speed || 0.5)));
const FLIGHT_DUR = (ft) => Math.max(300, Math.min(1400, (ft || 0.5) * FLIGHT_SCALE));

// Home positions, aligned with engine._home_position (team -> slot -> [x, y]).
const HOME = { 0: { 1: [2.5, 3.0], 2: [5.5, 5.0] }, 1: { 1: [2.5, 13.0], 2: [5.5, 11.0] } };

// action_hint / parsed action -> pose key for the humanoid figure.
const ACTION_POSE = {
  SERVE: "serve", DIG: "dig", SET: "set", SPIKE: "spike", PLACE: "spike", BLOCK: "block",
};

function normalizePos(v) {
  if (!v) return null;
  if (Array.isArray(v)) return { x: v[0], y: v[1], z: 0 };
  return v;
}

export class MatchState {
  constructor(teams) {
    this.teams = teams;
    this.players = [];
    this.ball = { x: 4, y: 8, z: 0 };
    this.score = { sets: [0, 0], points: [0, 0], server: 0 };
    this.winner = null;
    this.lastActor = null;
    this.server = null;
    this.pulse = {};

    teams.forEach((team, ti) => {
      (team.players || []).forEach((p) => {
        const home = HOME[ti][p.slot];
        this.players.push({
          slot: p.slot,
          teamIndex: ti,
          teamName: team.name,
          label: `${ti === 0 ? "A" : "B"}${p.slot}`,
          x: home[0],
          y: home[1],
          action: "idle",
          facing: 1,
        });
      });
    });
  }

  find(teamName, slot) {
    return this.players.findIndex((p) => p.teamName === teamName && p.slot === slot);
  }

  setPos(idx, x, y) {
    if (idx >= 0) {
      this.players[idx].x = x;
      this.players[idx].y = y;
    }
  }
}

export class ReplayEngine {
  constructor(teams, events) {
    this.teams = teams;
    this.events = events || [];
    this.segments = this.build();
    this.duration = this.segments.length
      ? this.segments[this.segments.length - 1].end
      : 0;
    this.t = 0;
    this.speed = 1;
    this.playing = false;
    this.state = new MatchState(teams);
    this.applyProgress(0);
  }

  build() {
    const segments = [];
    const pos = {};
    const key = (teamName, slot) => `${teamName}::${slot}`;

    // Seed tracked positions with home formation.
    this.teams.forEach((team, ti) => {
      (team.players || []).forEach((p) => {
        pos[key(team.name, p.slot)] = [...HOME[ti][p.slot]];
      });
    });

    let cursor = 0;
    // A concurrent segment shares the start of the preceding ball flight (the
    // receiver's run happens *during* the flight, meeting the ball at landing).
    const push = (type, dur, data, startOverride) => {
      const start = startOverride === undefined ? cursor : startOverride;
      segments.push({ type, start, dur, end: start + dur, ...data });
      if (startOverride === undefined) cursor += dur;
    };
    let lastBall = null;

    for (const ev of this.events) {
      const p = ev.payload || {};
      const k = key(p.team_name, p.slot);
      // Only an INTERCEPT immediately after a TRAJECTORY reuses the flight timing.
      if (ev.event_type !== "INTERCEPT") lastBall = null;

      if (ev.event_type === "RALLY_STARTED") {
        const positions = [];
        this.teams.forEach((team, ti) => {
          (team.players || []).forEach((pl) => {
            const kk = key(team.name, pl.slot);
            positions.push({ teamName: team.name, slot: pl.slot, from: pos[kk], to: HOME[ti][pl.slot] });
            pos[kk] = [...HOME[ti][pl.slot]];
          });
        });
        push("form", 350, { positions });
      } else if (ev.event_type === "DECISION") {
        const from = p.from_pos || pos[k];
        const to = p.move_to || (p.parsed && p.parsed.move_to) || from;
        const speed = p.move_speed || (p.parsed && p.parsed.move_speed) || 0.5;
        // Server visibly steps back to the line before serving.
        if (p.action_hint === "SERVE" && from) {
          const home = this._homeOf(p.team_name, p.slot);
          if (home && (from[0] !== home[0] || from[1] !== home[1])) {
            push("move", 250, { teamName: p.team_name, slot: p.slot, from: home, to: from });
          }
        }
        push("move", MOVE_DUR(speed), {
          teamName: p.team_name, slot: p.slot, from, to,
          actor: true, serve: p.action_hint === "SERVE",
          action: ACTION_POSE[(p.parsed && p.parsed.action) || p.action_hint] || "run",
        });
        pos[k] = to;
      } else if (ev.event_type === "TRAJECTORY") {
        const from = normalizePos(p.from_ball) || { x: 4, y: 8, z: 0 };
        const to = p.ball || from;
        const peak = Math.max(2.0, (p.flight_time || 0.5) * 3.5);
        const dur = FLIGHT_DUR(p.flight_time);
        push("ball", dur, { from, to, peak });
        lastBall = { start: segments[segments.length - 1].start, dur };
      } else if (ev.event_type === "INTERCEPT") {
        const from = pos[k] || p.at;
        if (lastBall) {
          // The receiver runs during the flight and meets the ball at landing.
          push("move", lastBall.dur, { teamName: p.team_name, slot: p.slot, from, to: p.at }, lastBall.start);
        } else {
          push("move", MOVE_DUR(0.7), { teamName: p.team_name, slot: p.slot, from, to: p.at });
        }
        pos[k] = p.at;
      } else if (ev.event_type === "BLOCK") {
        push("pulse", 350, { teamName: p.team_name, slot: p.slot });
      } else if (
        ev.event_type === "POINT" ||
        ev.event_type === "SET_WON" ||
        ev.event_type === "MATCH_FINISHED"
      ) {
        push("score", 0, { state: p.payload || {} });
      }
    }
    return segments;
  }

  _homeOf(teamName, slot) {
    const team = this.teams.find((t) => t.name === teamName);
    if (!team) return null;
    const ti = this.teams.indexOf(team);
    return HOME[ti][slot];
  }

  applySegment(seg, local) {
    const st = this.state;
    if (seg.type === "move") {
      const idx = st.find(seg.teamName, seg.slot);
      if (idx < 0) return;
      const from = seg.from;
      const to = seg.to;
      if (from && to) {
        st.setPos(idx, from[0] + (to[0] - from[0]) * local, from[1] + (to[1] - from[1]) * local);
      } else if (to) {
        st.setPos(idx, to[0], to[1]);
      }
      if (from && to && to[0] !== from[0]) {
        st.players[idx].facing = to[0] > from[0] ? 1 : -1;
      }
      if (seg.actor) st.lastActor = idx;
      if (seg.serve) st.server = idx;
      st.players[idx].action = seg.action || "run";
    } else if (seg.type === "form") {
      (seg.positions || []).forEach((pp) => {
        const idx = st.find(pp.teamName, pp.slot);
        if (idx < 0) return;
        if (pp.from && pp.to) {
          st.setPos(idx, pp.from[0] + (pp.to[0] - pp.from[0]) * local, pp.from[1] + (pp.to[1] - pp.from[1]) * local);
        } else if (pp.to) {
          st.setPos(idx, pp.to[0], pp.to[1]);
        }
        st.players[idx].action = "run";
      });
    } else if (seg.type === "ball") {
      const f = seg.from;
      const t = seg.to;
      st.ball.x = f.x + (t.x - f.x) * local;
      st.ball.y = f.y + (t.y - f.y) * local;
      st.ball.z = local >= 1 ? t.z || 0 : Math.sin(Math.PI * local) * seg.peak;
    } else if (seg.type === "pulse") {
      const idx = st.find(seg.teamName, seg.slot);
      if (idx >= 0) {
        st.pulse[idx] = seg.start;
        st.players[idx].action = "block";
      }
    } else if (seg.type === "score" && seg.state) {
      const s = seg.state;
      if (Array.isArray(s.set_points)) st.score.points = s.set_points;
      if (Array.isArray(s.sets_won)) st.score.sets = s.sets_won;
      if (typeof s.server === "number") st.score.server = s.server;
      if (typeof s.winner === "number") st.winner = s.winner;
    }
  }

  applyProgress(t) {
    this.state = new MatchState(this.teams);
    for (const seg of this.segments) {
      if (seg.start > t) break;
      const local = Math.min(1, (t - seg.start) / Math.max(0.0001, seg.dur));
      this.applySegment(seg, local);
    }
    this.t = t;
    return this.state;
  }

  seek(t) {
    const clamped = Math.max(0, Math.min(this.duration, t));
    this.applyProgress(clamped);
    return clamped;
  }
}
