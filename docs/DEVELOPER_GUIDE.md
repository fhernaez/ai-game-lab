# AI Game Lab — Developer Guide (Beach Volleyball)

This guide explains the V3 architecture and how to customize and extend the
beach-volleyball application.

---

## 1. Architecture

```text
Browser (Jinja2 + HTMX + vanilla JS)
   |
   v
web/            routes + templates + static (sim/)
   |
   v
application/    matchmaking, presence, team, match, settings services
   |
   v
domain/volleyball/   brain/ body/ core/ engine  (no Flask)
   |
   v
infrastructure/ LLM provider registry, database (SQLAlchemy), Redis/rq queue
```

Key rules:

- **Domain is Flask-free** (`app/domain/volleyball/*`).
- **No game logic in routes**; routes call services, services call the domain.
- **The graphical simulation is independent** — `app/web/static/js/sim/`
  consumes only the event stream; replace it without touching anything else.
- **Seeded randomness** — the match engine uses a seeded `random.Random`, so matches are
  reproducible.

## 2. Repository layout

```
app/
├── web/            # auth, users, settings, matchmaking, teams, matches, history, api
│   ├── templates/  # base, auth, users, settings, matchmaking, teams, matches, history
│   └── static/js/sim/   # independent simulation module
├── application/    # matchmaking_service, presence_service, team_service, match_service,
│                   #   settings_service, seed
├── domain/volleyball/
│   ├── brain/      # agent.py, skills.py, tools.py, sensors.py, memory.py,
│   │               #   decision.py, render.py (agent file view)
│   ├── body/       # body.py, actuators.py, parameters.py (7 skills, budget, archetypes)
│   ├── core/       # rules.py, physics.py, world.py, defaults.py (admin-editable knobs),
│   │               #   render.py (core file view)
│   ├── engine.py   # MatchEngine
│   └── events.py   # event types
├── infrastructure/ # llm/ (registry, mock, openai_compatible), queue.py
└── models.py       # Match, Team, Player, Event, User, AppSetting
```

## 3. The match engine

`app/domain/volleyball/engine.py` runs a time-based, message-driven match. Each rally is a
serve (LLM message + decision) whose trajectory is computed by the deterministic core
(`physics.py`): it adds a seeded random offset, computes the **flight time**, and lets the
defending players **move to intercept** — whoever reaches the ball first plays the next
touch. The core scores when the ball lands.

- `core/physics.py` — trajectory (`resolve_shot`), `flight_time`, `reach_time`/`can_reach`.
- `brain/decision.py` — the message + decision protocol (ball hit **and** the player's own
  `move_to`/`move_speed` movement) and the shared-rally-context prompt.
- `events.py` — `DECISION` (with `from_pos`, `move_to`, `move_speed`), `TRAJECTORY`,
  `INTERCEPT`, `BLOCK`, `POINT`, etc.
- Every agent's message is accumulated and shared to later agents in the rally.

The deterministic core also enforces the fault set — `net`, `out`, `net_touch`,
`illegal_attack`, `four_touches` — and attempts a `BLOCK` on fast attacks. Players'
`move_to` is clamped to their own half (no crossing the net).

Events are **persisted incrementally** — `match_service._run` commits each event as the
engine emits it (via an `on_event` callback), so the live view updates in real time. A
failed event write marks the match `failed` (never silently empty). `start_match` is
idempotent: it refuses to enqueue a match that is already `queued` or `running`.

`match_service.build_teams()` materializes the DB teams into the dicts the engine expects;
`match_service._make_resolver()` builds the `resolve(model_ref) -> (provider, model)`
callable from the LLM registry.

## 4. Extending

### 4.1 Tune the physics / rules (admin)

The tunable rules and physics constants live in `app/domain/volleyball/core/defaults.py`
(`KNOBS`), each with a `what`/`effect` description and `min`/`max`/`step`. Administrators
edit them in **Settings → Core files**; the values are stored as `AppSetting` rows and a
match snapshots the resolved values (`Match.core_config_json`) at start, so history never
changes when the knobs change. Students read the same files read-only.

### 4.2 Add a provider

Add an entry to `LLM_PROVIDERS` (OpenAI-compatible, including Ollama — no code). For a new
provider *type*, subclass `LLMProvider` in `app/infrastructure/llm/` and register it in
`registry.py:build_registry`.

### 4.3 Add a model / migration

Add to `app/models.py`, then `flask db migrate` + `flask db upgrade`.

### 4.4 Add a page

Create a blueprint in `app/web/`, register it in `app/__init__.py:register_blueprints`,
add templates, and a nav link in `base.html`.

### 4.5 Customize the court animation

The simulation is a set of ES modules in `app/web/static/js/sim/` (`court.js`,
`renderer.js`, `replay.js`, `live.js`, `main.js`), loaded from
`matches/view.html` as `<script type="module">`. It consumes only
`/api/matches/<id>/state` and `/events`. No other code depends on it — replace or
upgrade it freely.

### 4.6 The Advanced view

A player's config is stored as structured JSON (`brain` + `body`). The Advanced view
(`teams/advanced.html`) serializes it read-only into the file view (`agent.md`,
`skills/*.md`, `tools.yaml`, `body.yaml`) via `brain/render.py` and `core/render.py`.
Editing happens through the structured form in `teams/configure.html`.

## 5. Conventions

- Domain Flask-free; services between routes and domain.
- Secrets in env only; never in the DB or rendered files.
- No arbitrary code execution; every LLM decision is validated/clamped.
- Version the rules; match history must never change when the rules change.

## 6. Testing

```bash
pytest
```

Add tests for rules, attributes/budget, physics determinism, team config, matchmaking
lifecycle, and history.
