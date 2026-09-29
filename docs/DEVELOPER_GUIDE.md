# AI Game Lab — Developer Guide (Beach Volleyball)

This guide explains the V3 architecture and how to customize and extend the
beach-volleyball application.

---

## 1. Architecture

```text
Browser (Jinja2 + HTMX + vanilla JS)
   |
   v
web/            routes + templates + static (volleyball_court.js)
   |
   v
application/    matchmaking, presence, team, match, settings services
   |
   v
domain/volleyball/   state, rules, physics, attributes, engine, decisions  (no Flask)
   |
   v
infrastructure/ LLM provider registry, database (SQLAlchemy), Redis/rq queue
```

Key rules:

- **Domain is Flask-free** (`app/domain/volleyball/*`).
- **No game logic in routes**; routes call services, services call the domain.
- **The graphical simulation is independent** — `app/web/static/js/volleyball_court.js`
  consumes only the event stream; replace it without touching anything else.
- **Seeded randomness** — the match engine uses a seeded `random.Random`, so matches are
  reproducible.

## 2. Repository layout

```
app/
├── web/            # auth, users, settings, matchmaking, teams, matches, history, api
│   ├── templates/  # base, auth, users, settings, matchmaking, teams, matches, history
│   └── static/js/volleyball_court.js   # independent simulation module
├── application/    # matchmaking_service, presence_service, team_service, match_service,
│                   #   settings_service, seed
├── domain/volleyball/
│   ├── state.py    # CourtState
│   ├── rules.py    # win condition, faults, possession, court switch
│   ├── physics.py  # stochastic serve/flight/defense
│   ├── attributes.py  # 7 skills, point-buy, difficulty, archetypes
│   ├── decisions.py   # decision protocol + prompt assembly
│   ├── engine.py      # MatchEngine
│   └── events.py      # event types
├── infrastructure/ # llm/ (registry, mock, openai_compatible), queue.py
└── models.py       # Match, Team, Player, Event, User, AppSetting
```

## 3. The match engine

`app/domain/volleyball/engine.py` runs a full match: for each set (best of 3), a loop of
rallies; each rally is a serve (LLM decision + physics) followed by alternating 3-touch
possessions until a fault/point. Every play emits `DECISION`, `TOUCH`, `FAULT`, `POINT`
events that drive both the interaction log and the court animation.

`match_service.build_teams()` materializes the DB teams into the dicts the engine
expects; `match_service._make_resolver()` builds the `resolve(model_ref) -> (provider,
model)` callable from the LLM registry.

## 4. Extending

### 4.1 Tune the physics

Edit `app/domain/volleyball/physics.py` (serve/attack/receive/set formulas) and
`attributes.py` (skill list, cost, difficulty budgets, archetypes). Keep everything
deterministic (use the passed `rng`).

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

Edit `app/web/static/js/volleyball_court.js` only — it reads `/api/matches/<id>/state` and
`/events` and renders the court. No other code depends on it.

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
