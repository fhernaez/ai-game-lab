/*
 * court.js — court geometry and the 2.5D perspective projection.
 *
 * World coordinates match the game domain: X is the court width (0..8), Y is the
 * length (0..16, camera near y=0, far y=16), Z is height (0..~5). The net sits at
 * Y = 8, height 2.43. A fixed elevated camera behind the near end line projects the
 * world onto the screen with one-point perspective.
 */

export const WORLD = { WIDTH: 8, LENGTH: 16, NET_Y: 8, NET_HEIGHT: 2.43 };

export const TEAM_COLORS = ["#38bdf8", "#fbbf24"];

export class Perspective {
  constructor(w, h) {
    this.w = w;
    this.h = h;
    this.F = 6;                  // perspective strength (smaller = more foreshortening)
    this.horizon = h * 0.30;     // far end line screen Y
    this.nearBottom = h * 0.92;  // near end line screen Y
    this.margin = 40;
    this.unit = (w - this.margin * 2) / WORLD.WIDTH; // px per meter at y = 0
    this.centerX = w / 2;
  }

  depth(y) {
    return this.F / (this.F + y); // 1 at y=0, ~0.27 at y=16
  }

  sy(y) {
    return this.horizon + (this.nearBottom - this.horizon) * this.depth(y);
  }

  sx(x, y) {
    return this.centerX + (x - WORLD.WIDTH / 2) * this.unit * this.depth(y);
  }

  // 3D world point -> screen; z lifts up, scaled by depth.
  project(x, y, z = 0) {
    return {
      x: this.sx(x, y),
      y: this.sy(y) - z * this.unit * this.depth(y),
      s: this.depth(y),
    };
  }
}
