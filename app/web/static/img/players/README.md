# Player sprites

Drop humanoid player sprites here to replace the procedural stick figures. The
simulation loads them automatically and falls back to the built-in figure when a
sprite is missing.

## Naming convention

```
{team}-{view}-{action}.png
```

- `team`: `a` (team 0, blue) or `b` (team 1, yellow).
- `view`: `front` or `back`. Because the camera sits behind one end line, players on
  the **near half** are seen from the **back**, players on the **far half** from the
  **front**. You need one image per view.
- `action`: one of `idle`, `run`, `serve`, `dig`, `set`, `spike`, `block`, `jump`.

Examples: `a-back-run.png`, `a-front-run.png`, `b-back-spike.png`, `b-front-spike.png`.

The figure is mirrored horizontally at runtime to face left/right, so you only need
one left/right orientation per (team, view, action).

## Guidelines

- Transparent PNG, roughly 1:1.6 aspect ratio (a standing figure).
- The figure's feet anchor to the bottom edge; the renderer scales it by court depth.
- To swap a look later, just replace the file — no code change is required.

Recommended free sources: Kenney.nl (e.g. "Toon Characters"), OpenGameArt.
