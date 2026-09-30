/*
 * court.js — court geometry and world→screen projection.
 *
 * World coordinates match the game domain: X is the court width (0..8), Y is the
 * length (0..16), and the net sits at Y = 8. The court is drawn top-down with the
 * long axis (Y) running horizontally on screen.
 */

export const WORLD = { WIDTH: 8, LENGTH: 16, NET_Y: 8, NET_HEIGHT: 2.43 };

export const TEAM_COLORS = ["#38bdf8", "#fbbf24"];

export class Projection {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.pad = 24;
    this.marginX = 60;
    this.courtPx = w - this.marginX * 2;
    this.courtH = h - this.pad * 2;
  }

  // world (x = width, y = length) -> screen
  sx(x) { return this.pad + (x / WORLD.WIDTH) * this.courtH; }
  sy(y) { return this.marginX + (y / WORLD.LENGTH) * this.courtPx; }
}
