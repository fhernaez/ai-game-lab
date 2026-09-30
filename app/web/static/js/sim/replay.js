/*
 * replay.js — deterministic event-log → timeline engine.
 *
 * Compiles the event stream into animation segments with cumulative start times,
 * then renders any point in time by replaying segments up to t. This gives
 * play / pause / seek / speed with a single applyProgress(t) method.
 */

const FLIGHT_SCALE = 800;
const MOVE_DUR = (speed) => Math.max(250, Math.min(1800, 900 / (speed || 0.5)));
const FLIGHT_DUR = (ft) => Math.max(350, Math.min(2200, (ft || 0.5) * FLIGHT_SCALE));

export class MatchState {
  constructor(teams) {
    this.teams = teams;
    this.players = [];
    this.ball = { x: 4, y: 8, z: 0 };
    this.score = { sets: [0, 0], points: [0, 0], server: 0 };
    this.winner = null;
    this.lastActor = null;
    this.pulse = {};

    const homes = { 0: [[2, 3], [6, 5]], 1: [[2, 11], [6, 13]] };
    teams.forEach((team, ti) => {
      (team.players || []).forEach((p, pi) => {
        const home = homes[ti][pi % 2];
        this.players.push({
          slot: p.slot,
          teamIndex: ti,
          teamName: team.name,
          label: `${ti === 0 ? "A" : "B"}${p.slot}`,
          x: home[0],
          y: home[1],
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
    let cursor = 0;
    const key = (teamName, slot) => `${teamName}::${slot}`;
    const push = (type, dur, data) => {
      segments.push({ type, start: cursor, dur, end: cursor + dur, ...data });
      cursor += dur;
    };

    for (const ev of this.events) {
      const p = ev.payload || {};
      const k = key(p.team_name, p.slot);

      if (ev.event_type === "DECISION") {
        const from = p.from_pos || pos[k];
        const to = p.move_to || (p.parsed && p.parsed.move_to) || from;
        const speed = p.move_speed || (p.parsed && p.parsed.move_speed) || 0.5;
        push("move", MOVE_DUR(speed), {
          teamName: p.team_name, slot: p.slot, from, to, actor: true,
        });
        pos[k] = to;
      } else if (ev.event_type === "TRAJECTORY") {
        const from = p.from_ball || { x: 4, y: 8, z: 0 };
        const to = p.ball || from;
        push("ball", FLIGHT_DUR(p.flight_time), { from, to });
      } else if (ev.event_type === "INTERCEPT") {
        const from = pos[k] || p.at;
        push("move", MOVE_DUR(0.7), {
          teamName: p.team_name, slot: p.slot, from, to: p.at,
        });
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
      if (seg.actor) st.lastActor = idx;
    } else if (seg.type === "ball") {
      const f = seg.from;
      const t = seg.to;
      st.ball.x = f.x + (t.x - f.x) * local;
      st.ball.y = f.y + (t.y - f.y) * local;
      const peak = Math.max(1.5, (f.z || 0) + (t.z || 0) + 1.0);
      st.ball.z = local >= 1 ? t.z || 0 : Math.sin(Math.PI * local) * peak;
    } else if (seg.type === "pulse") {
      const idx = st.find(seg.teamName, seg.slot);
      if (idx >= 0) st.pulse[idx] = seg.start;
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
