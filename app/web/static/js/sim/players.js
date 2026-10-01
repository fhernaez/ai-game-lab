/*
 * players.js — humanoid player figures.
 *
 * Each player is drawn as a small humanoid figure whose limbs are posed per movement
 * (idle / run / serve / dig / set / spike / block / jump). Because the camera sits
 * behind one end line, players on the near half are seen from the BACK and players on
 * the far half from the FRONT, so a figure has two views. Optional sprites can be
 * dropped into `img/players/` as `{team}-{view}-{action}.png`; when present they
 * override the built-in procedural figure. Missing sprites fall back silently.
 */

import { TEAM_COLORS } from "./court.js";

const ACTIONS = ["idle", "run", "serve", "dig", "set", "spike", "block", "jump"];
const VIEWS = ["front", "back"];

const sprites = {}; // cache key -> HTMLImageElement

function spriteKey(teamIndex, view, action) {
  return `${teamIndex === 0 ? "a" : "b"}-${view}-${action}`;
}

export function loadPlayerSprites() {
  for (const team of ["a", "b"]) {
    for (const view of VIEWS) {
      for (const action of ACTIONS) {
        const img = new Image();
        img.onload = () => {
          sprites[`${team}-${view}-${action}`] = img;
        };
        img.src = `/static/img/players/${team}-${view}-${action}.png`;
      }
    }
  }
}

// Limb pose angles (radians). 0 = straight down, negative = up, +x = to the right.
function pose(action, tMs) {
  const swing = Math.sin(tMs / 110) * 0.55; // running/leg swing
  switch (action) {
    case "serve":
      return { armL: -0.3, armR: -2.7, legL: 0.35, legR: -0.25 };
    case "dig":
      return { armL: 0.5, armR: 0.5, legL: 0.5, legR: 0.25 };
    case "set":
      return { armL: -2.9, armR: -2.9, legL: 0.2, legR: 0.2 };
    case "spike":
      return { armL: 0.3, armR: -3.0, legL: 0.1, legR: -0.4 };
    case "block":
      return { armL: -2.9, armR: -2.9, legL: 0.2, legR: 0.2 };
    case "jump":
      return { armL: -2.5, armR: -2.5, legL: 0.7, legR: 0.7 };
    case "run":
      return { armL: swing, armR: -swing, legL: -swing, legR: swing };
    default:
      return { armL: -0.15, armR: -0.15, legL: 0.15, legR: 0.15 };
  }
}

export function drawPlayerFigure(ctx, x, y, s, teamIndex, view, action, facing, tMs) {
  const sprite = sprites[spriteKey(teamIndex, view, action)];
  if (sprite && sprite.complete) {
    const w = 34 * s;
    const h = 54 * s;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(facing || 1, 1);
    ctx.drawImage(sprite, -w / 2, -h, w, h);
    ctx.restore();
    return;
  }
  drawProcedural(ctx, x, y, s, teamIndex, view, action, facing, tMs);
}

function drawProcedural(ctx, x, y, s, teamIndex, view, action, facing, tMs) {
  const color = TEAM_COLORS[teamIndex];
  const p = pose(action, tMs);
  const f = facing || 1;

  const headR = 6 * s;
  const headY = y - 34 * s;
  const shoulderY = y - 26 * s;
  const hipY = y - 13 * s;
  const armLen = 11 * s;
  const legLen = 13 * s;

  ctx.strokeStyle = color;
  ctx.lineCap = "round";

  // Legs (hips -> feet).
  limb(ctx, x, hipY, p.legL, legLen, color, 3.5 * s, f);
  limb(ctx, x, hipY, p.legR, legLen, color, 3.5 * s, f);

  // Torso.
  ctx.lineWidth = 4 * s;
  ctx.beginPath();
  ctx.moveTo(x, hipY);
  ctx.lineTo(x, shoulderY);
  ctx.stroke();

  // Arms (shoulders -> hands).
  limb(ctx, x, shoulderY, p.armL, armLen, color, 3 * s, f);
  limb(ctx, x, shoulderY, p.armR, armLen, color, 3 * s, f);

  // Head.
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, headY, headR, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 1.2 * s;
  ctx.stroke();

  // Face (front view only): two eyes looking toward the camera.
  if (view === "front") {
    const eyeR = headR * 0.16;
    ctx.fillStyle = "#0f172a";
    ctx.beginPath();
    ctx.arc(x - headR * 0.3, headY, eyeR, 0, Math.PI * 2);
    ctx.arc(x + headR * 0.3, headY, eyeR, 0, Math.PI * 2);
    ctx.fill();
  }
}

function limb(ctx, x, y0, angle, len, color, width, facing) {
  const ex = x + (facing || 1) * Math.sin(angle) * len;
  const ey = y0 + Math.cos(angle) * len;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(x, y0);
  ctx.lineTo(ex, ey);
  ctx.stroke();
}
