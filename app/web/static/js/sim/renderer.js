/*
 * renderer.js — Canvas 2.5D perspective renderer (fixed camera behind the near end
 * line). Draws the court as a perspective trapezoid, a vertical translucent net,
 * depth-scaled players, and a shaded ball with a ground shadow and motion trail.
 */

import { WORLD, TEAM_COLORS, Perspective } from "./court.js";

const BALL_R = 6;

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.resize();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width || 960;
    this.height = Math.round(this.width * 0.6); // taller canvas for perspective
    this.canvas.width = Math.round(this.width * dpr);
    this.canvas.height = Math.round(this.height * dpr);
    this.canvas.style.height = `${this.height}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.proj = new Perspective(this.width, this.height);
  }

  draw(state, t, trail) {
    const ctx = this.ctx;
    const P = this.proj;
    const W = this.width;
    const H = this.height;

    ctx.clearRect(0, 0, W, H);

    // 1. Background sky gradient.
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, "#0b1220");
    bg.addColorStop(1, "#1c2a44");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // 2. Court trapezoid (sand).
    const bl = P.project(0, 0, 0);
    const br = P.project(WORLD.WIDTH, 0, 0);
    const tr = P.project(WORLD.WIDTH, WORLD.LENGTH, 0);
    const tl = P.project(0, WORLD.LENGTH, 0);
    const sand = ctx.createLinearGradient(0, bl.y, 0, tl.y);
    sand.addColorStop(0, "#f59e0b");
    sand.addColorStop(1, "#d97706");
    ctx.fillStyle = sand;
    ctx.beginPath();
    ctx.moveTo(bl.x, bl.y);
    ctx.lineTo(br.x, br.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.lineTo(tl.x, tl.y);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#fef3c7";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Court lines (sidelines, end lines, center line).
    this.groundLine(0, 0, 0, WORLD.LENGTH, "rgba(254,243,199,0.8)", 1);
    this.groundLine(WORLD.WIDTH, 0, WORLD.WIDTH, WORLD.LENGTH, "rgba(254,243,199,0.8)", 1);
    this.groundLine(0, WORLD.NET_Y, WORLD.WIDTH, WORLD.NET_Y, "rgba(254,243,199,0.5)", 1);

    // 3. Ground shadows (ball + players).
    this.drawBallShadow(state.ball);
    state.players.forEach((pl) => this.drawPlayerShadow(pl));

    // 4. Depth-sort entities around the net.
    const ents = state.players.map((pl, i) => ({ pl, i }));
    const far = ents.filter((e) => e.pl.y > WORLD.NET_Y).sort((a, b) => b.pl.y - a.pl.y);
    const near = ents.filter((e) => e.pl.y <= WORLD.NET_Y).sort((a, b) => b.pl.y - a.pl.y);
    const ballFar = state.ball.y > WORLD.NET_Y;

    // 5. Far half (behind the net).
    far.forEach((e) => this.drawPlayer(e.pl, state, t, e.i));
    if (ballFar) this.drawBall(state.ball, trail);

    // 6. Net.
    this.drawNet();

    // 7. Near half (in front of the net).
    near.forEach((e) => this.drawPlayer(e.pl, state, t, e.i));
    if (!ballFar) this.drawBall(state.ball, trail);

    // 8. Serve badge above the serving player.
    this.drawServeBadge(state);
  }

  groundLine(x1, y1, x2, y2, color, width) {
    const a = this.proj.project(x1, y1, 0);
    const b = this.proj.project(x2, y2, 0);
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = width;
    this.ctx.beginPath();
    this.ctx.moveTo(a.x, a.y);
    this.ctx.lineTo(b.x, b.y);
    this.ctx.stroke();
  }

  drawNet() {
    const ctx = this.ctx;
    const P = this.proj;
    const y = WORLD.NET_Y;
    const h = WORLD.NET_HEIGHT;
    const bl = P.project(0, y, 0);
    const br = P.project(WORLD.WIDTH, y, 0);
    const tl = P.project(0, y, h);
    const tr = P.project(WORLD.WIDTH, y, h);

    ctx.fillStyle = "rgba(226,232,240,0.16)";
    ctx.beginPath();
    ctx.moveTo(bl.x, bl.y);
    ctx.lineTo(br.x, br.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.lineTo(tl.x, tl.y);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = "rgba(248,250,252,0.85)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(tl.x, tl.y);
    ctx.lineTo(tr.x, tr.y);
    ctx.stroke();

    ctx.strokeStyle = "rgba(248,250,252,0.25)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 8; i++) {
      const x = (WORLD.WIDTH * i) / 8;
      const b = P.project(x, y, 0);
      const t = P.project(x, y, h);
      ctx.beginPath();
      ctx.moveTo(b.x, b.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    }

    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 3;
    [0, WORLD.WIDTH].forEach((x) => {
      const b = P.project(x, y, 0);
      const t = P.project(x, y, h + 0.1);
      ctx.beginPath();
      ctx.moveTo(b.x, b.y);
      ctx.lineTo(t.x, t.y);
      ctx.stroke();
    });
  }

  drawBallShadow(ball) {
    const ctx = this.ctx;
    const P = this.proj;
    const sp = P.project(ball.x, ball.y, 0);
    const alpha = Math.max(0.08, 0.35 - (ball.z || 0) * 0.06);
    ctx.fillStyle = `rgba(0,0,0,${alpha})`;
    ctx.beginPath();
    ctx.ellipse(sp.x, sp.y, BALL_R * sp.s * 1.2, BALL_R * sp.s * 0.5, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  drawPlayerShadow(pl) {
    const ctx = this.ctx;
    const P = this.proj;
    const sp = P.project(pl.x, pl.y, 0);
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.beginPath();
    ctx.ellipse(sp.x, sp.y + 6 * sp.s, 12 * sp.s, 5 * sp.s, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  drawBall(ball, trail) {
    const ctx = this.ctx;
    const P = this.proj;

    if (trail && trail.length) {
      for (let i = 0; i < trail.length; i++) {
        const tp = trail[i];
        const alpha = ((i + 1) / trail.length) * 0.3;
        const pp = P.project(tp.x, tp.y, tp.z);
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.beginPath();
        ctx.arc(pp.x, pp.y, BALL_R * pp.s * 0.75, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    const pp = P.project(ball.x, ball.y, ball.z);
    const r = BALL_R * pp.s;

    ctx.shadowColor = "rgba(255,255,255,0.8)";
    ctx.shadowBlur = 12;
    const g = ctx.createRadialGradient(pp.x - r * 0.3, pp.y - r * 0.3, r * 0.1, pp.x, pp.y, r);
    g.addColorStop(0, "#ffffff");
    g.addColorStop(0.7, "#e2e8f0");
    g.addColorStop(1, "#94a3b8");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(pp.x, pp.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 1.2;
    ctx.stroke();

    ctx.strokeStyle = "rgba(15,23,42,0.45)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pp.x - r, pp.y);
    ctx.quadraticCurveTo(pp.x, pp.y - r * 0.5, pp.x + r, pp.y);
    ctx.moveTo(pp.x - r * 0.6, pp.y - r * 0.7);
    ctx.quadraticCurveTo(pp.x, pp.y - r * 1.1, pp.x + r * 0.6, pp.y - r * 0.7);
    ctx.stroke();
  }

  drawPlayer(pl, state, t, i) {
    const ctx = this.ctx;
    const P = this.proj;
    const pp = P.project(pl.x, pl.y, 0);
    const r = 14 * pp.s;

    let pr = r;
    if (state.pulse && typeof state.pulse[i] === "number" && t - state.pulse[i] < 350) pr = r * 1.35;

    if (state.lastActor === i) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(pp.x, pp.y, pr + 4 * pp.s, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.fillStyle = TEAM_COLORS[pl.teamIndex];
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(pp.x, pp.y, pr, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#0f172a";
    ctx.font = `bold ${Math.max(9, 11 * pp.s)}px system-ui`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(pl.label, pp.x, pp.y + 1);
  }

  drawServeBadge(state) {
    if (state.server == null) return;
    const pl = state.players[state.server];
    if (!pl) return;
    const ctx = this.ctx;
    const P = this.proj;
    const pp = P.project(pl.x, pl.y, 0);
    const y = pp.y - 22 * pp.s;
    const font = `bold ${Math.max(9, 10 * pp.s)}px system-ui`;
    ctx.font = font;
    const tw = ctx.measureText("SERVE").width + 12;
    const h = 15 * pp.s;

    ctx.fillStyle = "#059669";
    ctx.beginPath();
    ctx.rect(pp.x - tw / 2, y - h / 2, tw, h);
    ctx.fill();
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("SERVE", pp.x, y);
  }
}
