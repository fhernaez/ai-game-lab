# Coding Agent Prompt — AI Game Lab V3 (Beach Volleyball)

You are the lead software engineer implementing **AI Game Lab V3**, an educational,
multi-user web application focused on a **single game: beach volleyball**.

Read all files in this specification before writing code, especially
`VOLLEYBALL_SPEC.md`.

## Mission

Build a clean, maintainable, extensible Flask application where students:

1. log in and see who is online
2. create a match (choose difficulty) and invite another online player
3. accept/decline an invitation
4. configure their team of 2 players: athlete attributes (sliders 1–10), a preset
   archetype, an LLM model (from the provider list), and LLM model parameters — each with
   a plain-language explanation
5. mark ready; the match starts when both are ready
6. watch the graphical match simulation (players + ball on the court)
7. read the interaction log (decision, attributes, physics outcome per play)
8. browse match history (all matches stored in the database)
9. administrators manage users and settings

## Non-negotiable architecture

- Flask is the web layer, not the game engine.
- Keep the volleyball domain (state, rules, physics, attributes, engine) Flask-free in
  `app/domain/volleyball/`.
- Use application services between routes and domain.
- PostgreSQL + Redis (queue + presence); SQLAlchemy + Alembic; Flask-Login.
- Jinja2 + HTMX + a small amount of JavaScript.
- Multi-provider / multi-model LLM abstraction; models selected from `LLM_PROVIDERS`.
- **No generic game designer.** The game is beach volleyball, implemented once, well.
- **The graphical simulation is an independent module** (`volleyball_court.js`), driven
  only by the event stream, so it can be replaced without touching the rest of the app.
- Store the full interaction log (prompt, model, model params, raw + parsed decision,
  athlete attributes, physics outcome) on every `DECISION` event.
- Run in its own venv; ship `requirements.txt`.

## Educational UX

The two most important surfaces are:

1. **Team configuration** — athlete sliders (1–10) + archetypes + LLM model/params, every
   control with a plain-language explanation of how it changes behavior.
2. **The interaction log + match simulation** — the readable trace of how the result was
   reached.

## Main navigation

1. **General Settings** (admin): providers (env, read-only), editable model lists,
   global default model.
2. **User Administration** (admin): list/create/role/delete users; graceful duplicate
   handling (no 500).
3. **Matchmaking**: create match (difficulty), invite an online player, accept/decline,
   configure team, ready-up.
4. **Match**: live graphical simulation + interaction log; start/stop/delete controls.
5. **History**: browse all finished matches and their interaction logs.

## The volleyball engine

Implement `app/domain/volleyball/`:

- `state.py` — CourtState: ball `(x, y, z)`, scores, sets, server, touches, possession.
- `rules.py` — win condition (best of 3; 21/15, win by 2), court switch
  (`% 7` / `% 5`), 3-touch possession, block = touch #1, fault list.
- `physics.py` — stochastic serve/flight/defense using seeded RNG and the attribute
  trade-offs (power vs accuracy, distance vs precision, speed vs stamina).
- `attributes.py` — the 7 attributes, slider→float mapping, point-buy cost, difficulty
  budgets, archetypes.
- `engine.py` — MatchEngine: rally → point → set → match loop; calls the LLM for each
  decision and the physics for each touch; emits events.
- `decisions.py` / prompts — the structured decision protocol.

All randomness is seeded per match for reproducibility.

## Decision protocol

Each acting player's LLM returns a structured JSON decision:

```json
{"action": "SERVE"|"DIG"|"SET"|"SPIKE"|"PLACE"|"BLOCK", "power": 0.0..1.0, "target": [x, y]}
```

Validate schema; clamp power to `[0,1]`; clamp target to the court. On invalid output,
fall back to a deterministic default decision (never crash).

## Testing requirements

Implement tests for:

- authentication + presence
- user administration (create/role/delete, duplicate handling)
- team configuration (slider validation, point-buy budget, archetypes)
- difficulty budgets
- volleyball rules (win condition, court switch, faults, possession)
- physics (seeded determinism, in/out/net outcomes)
- match lifecycle (create/invite/accept/ready/start/stop/delete)
- interaction log persistence
- history browsing

## Implementation order

1. project skeleton (venv + requirements.txt)
2. configuration
3. database + migrations
4. authentication + presence
5. user administration
6. attributes (7 skills, point-buy, difficulty, archetypes)
7. volleyball domain (state, rules, physics)
8. match engine + decision protocol
9. LLM abstraction (multi-provider, params)
10. matchmaking
11. team configuration UI (sliders + archetypes + model select + explanations)
12. match view + interaction log
13. graphical simulation (independent module)
14. history
15. tests
16. Docker

## Code quality

Prefer simple explicit code. No microservices, no Kubernetes, no large frontend
framework. Pin dependencies. Document decisions in `docs/DECISIONS.md`.

## First milestone

> A user can log in, create a match at a difficulty, invite another user, both configure
> their 2 players (sliders + model), ready up, and watch one rally resolve (serve → a
> touch or two → point/fault) appear in the interaction log and the graphical simulation.
