/*
 * renderer.js — Canvas 2D renderer for the court, players, and ball.
 */

import { WORLD, TEAM_COLORS, Projection } from "./court.js";

const ARC_SCALE = 26;
const BALL_BASE_R = 4;

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.resize();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width || 880;
    this.height = (this.width * 460) / 880; // keep 880x460 aspect
    this.canvas.width = Math.round(this.width * dpr);
    this.canvas.height = Math.round(this.height * dpr);
    this.canvas.style.height = `${this.height}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.proj = new Projection(this.width, this.height);
  }

  draw(state, t) {
    const ctx = this.ctx;
    const p = this.proj;
    const W = this.width;
    const H = this.height;

    ctx.clearRect(0, 0, W, H);

    // Background.
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, W, H);

    // Court sand.
    ctx.fillStyle = "#f59e0b";
    ctx.fillRect(p.sy(0), p.sx(0), p.courtPx, p.courtH);
    ctx.strokeStyle = "#fef3c7";
    ctx.lineWidth = 2;
    ctx.strokeRect(p.sy(0), p.sx(0), p.courtPx, p.courtH);

    // Side + end lines (subtle).
    ctx.strokeStyle = "rgba(254,243,199,0.5)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(p.sy(0), p.sx(WORLD.WIDTH / 2));
    ctx.lineTo(p.sy(WORLD.LENGTH), p.sx(WORLD.WIDTH / 2));
    ctx.stroke();

    // Net band.
    ctx.fillStyle = "#e2e8f0";
    ctx.fillRect(p.sy(WORLD.NET_Y) - 2, p.sx(0), 4, p.courtH);

    // Serve marker on the serving team's side.
    if (state.score && typeof state.score.server === "number") {
      ctx.fillStyle = "#34d399";
      ctx.beginPath();
      const sideY = state.score.server === 0 ? 3 : WORLD.LENGTH - 3;
      ctx.arc(p.sy(sideY), p.sx(WORLD.WIDTH / 2), 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#052e1f";
      ctx.font = "bold 10px system-ui";
      ctx.textAlign = "center";
      ctx.fillText("SERVE", p.sy(sideY), p.sx(WORLD.WIDTH / 2) + 3);
    }

    // Players.
    state.players.forEach((pl, i) => {
      const color = TEAM_COLORS[pl.teamIndex];
      const cx = p.sy(pl.y);
      const cy = p.sx(pl.x);

      let r = 13;
      if (state.pulse && typeof state.pulse[i] === "number" && t - state.pulse[i] < 350) r = 18;

      // Last-actor highlight ring.
      if (state.lastActor === i) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, r + 5, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = color;
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#0f172a";
      ctx.font = "bold 11px system-ui";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(pl.label, cx, cy + 1);
    });

    // Ball shadow + ball.
    const bx = p.sy(state.ball.y);
    const by = p.sx(state.ball.x);
    const z = state.ball.z || 0;

    ctx.fillStyle = `rgba(0,0,0,${Math.max(0, 0.3 - z * 0.08)})`;
    ctx.beginPath();
    ctx.ellipse(bx, by, 4 + z * 1.5, 2 + z * 0.8, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(bx, by - z * ARC_SCALE, BALL_BASE_R + z * 2.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}
