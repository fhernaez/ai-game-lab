# AI Game Lab — Developer Guide

This guide explains how the application is structured and how to customize it with
precision, upgrade it safely, and add new modules and functionality.

It assumes you have read `STARTUP_GUIDE.md` and can run the app locally
(`flask --app run.py db upgrade`, `flask --app run.py seed`, `flask --app run.py run`).

---

## 1. Architecture at a glance

The application follows the four-layer model described in `specs/ARCHITECTURE.md`.

```text
Browser (Jinja2 + HTMX + vanilla JS)
   |
   v
web/            Flask routes + templates + static assets  (no game rules here)
   |
   v
application/    workflow services (matchmaking, presence, competition, crew, ...)
   |
   v
domain/         crew, dialogue runner, referee+guard, prompts, events (no Flask)
   |
   v
infrastructure/ LLM provider registry, database (SQLAlchemy), Redis/rq queue
```

Key rules that keep the codebase healthy:

- **Domain layer is Flask-free.** `app/domain/*` imports nothing from Flask.
- **No game mechanics in routes.** The web layer delegates to services and the generic
  dialogue runner.
- **Structured configuration is authoritative.** The DB stores a structured blueprint
  dict (`GameVersion.blueprint_json`); Markdown/YAML files are generated renders of it.
- **Deterministic compiler + round-trip.** The compiler and importer share the same
  validation (`app/application/validation.py`).
- **The game is a dialogue.** The runner (`app/domain/dialogue.py`) implements
  `speak → act → referee`, not per-game logic.

---

## 2. Repository layout

```text
AI-Edu-game-lab-app-v1/
├── config.py                 # Config classes + .env loading
├── run.py                    # dev entrypoint
├── wsgi.py                   # production entrypoint (gunicorn)
├── requirements.txt          # pinned dependencies
├── .env.example              # documented environment template
├── Dockerfile                # container image (gunicorn)
├── docker-compose.yml        # db + redis + app + worker (+ ollama profile)
├── docker/entrypoint.sh      # migrations + optional seed, then exec CMD
├── migrations/               # Alembic migrations (flask db ...)
├── game_templates/           # seed templates (one directory per game)
│   ├── debate/
│   └── team_sports/
├── app/
│   ├── __init__.py           # app factory + blueprint/CLI registration + presence hook
│   ├── extensions.py         # db, login_manager, migrate
│   ├── models.py             # SQLAlchemy models (Crew, CrewMember, Competition, ...)
│   ├── web/                  # HTTP layer
│   │   ├── auth.py settings.py games.py matchmaking.py
│   │   ├── competitions.py replay.py api.py
│   │   ├── templates/        # Jinja2 (base.html + per-area)
│   │   └── static/           # css/app.css, js/visualization.js
│   ├── application/          # services
│   │   ├── blueprint_service.py    # create/save/version games
│   │   ├── compiler_service.py     # blueprint -> files
│   │   ├── importer_service.py     # files -> blueprint (round-trip)
│   │   ├── validation.py           # shared validation rules
│   │   ├── crew_service.py         # default crew/member configs
│   │   ├── matchmaking_service.py  # invite/accept/decline/ready + crew creation
│   │   ├── presence_service.py     # who is online
│   │   ├── competition_service.py  # start/run/stop/delete competitions
│   │   ├── settings_service.py     # role defaults + provider model lists
│   │   └── seed.py                 # admin + template seeding
│   ├── domain/               # pure game logic
│   │   ├── crew.py           # Crew, CrewMember (role, speak order, params)
│   │   ├── dialogue.py       # DialogueRunner (speak → act → referee)
│   │   ├── referee.py        # Referee (LLM) + verdict guard (clamp_score)
│   │   ├── prompts.py        # prompt assembly (round history injected)
│   │   └── events.py         # event types + constructors
│   └── infrastructure/
│       ├── queue.py          # Redis/rq wrapper (sync fallback)
│       └── llm/              # LLM provider registry
│           ├── base.py       # LLMProvider, LLMResult
│           ├── mock.py       # deterministic offline provider (echoes mock_output)
│           ├── openai_compatible.py  # OpenAI / Ollama endpoints (full params)
│           ├── registry.py   # build_registry / resolve_model
│           └── __init__.py   # get_registry() / resolve_model()
├── tests/
│   ├── conftest.py           # app/client fixtures (temp DB)
│   └── test_app.py           # integration tests
└── docs/                     # user-facing guides
```

---

## 3. Development environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
cp .env.example .env
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py run
```

Run the tests after any change:

```bash
pytest
```

The test fixtures (`tests/conftest.py`) build a throwaway app against a temporary
SQLite database and seed it, so tests never touch your development database.

### Docker development

```bash
docker compose up -d --build
docker compose logs -f app worker
docker compose exec app flask --app run.py create-user ...
```

With `REDIS_URL` unset, runs execute synchronously (no worker needed) — convenient for
a local inner loop.

---

## 4. Core concept: the blueprint

A game is a Python dict stored in `GameVersion.blueprint_json`. Its top-level keys:

```text
game         id, name, version, description
competition  teams, default_round_budget, wall_clock_timeout_seconds
crew         roles [{id, speak_order, speaker, required}]
referee      enabled, role, response_format
resources    team_token_budget, team_memory_budget, max_concurrent_agents
dialogue     actions [{id}], scoring [{kind, ...}], win
playground   editable [...], locked [...]
markdown     game, rules, scoring, referee, agents {role: md}, skills {skill: md}
```

The `crew` block defines the crew members (roles, speak order, which one is the
speaker). The `dialogue` block defines the action schema and the scoring rules used by
the referee verdict guard.

The blueprint is rendered to files by `app/application/compiler_service.py` and parsed
back by `app/application/importer_service.py`; both call
`app/application/validation.py:validate_blueprint`.

---

## 5. The dialogue runner

`app/domain/dialogue.py:DialogueRunner` is game-agnostic. It reads the blueprint's
`crew` and `dialogue` blocks and, for each of `default_round_budget` rounds:

1. Emit `ROUND_STARTED`.
2. For each crew:
   - **SPEAK**: each member (in `speak_order`) produces one `CREW_MESSAGE` via its
     provider/model/params; the message is fed into the next member's prompt.
   - **ACT**: the speaker proposes a structured action (`ACTION_PROPOSED`).
   - **REFEREE**: the referee model returns a verdict (`REFEREE_VERDICT`), which
     `apply_guard` validates and clamps, then applies as `SCORE_CHANGED`/`STATE_CHANGED`.
3. Emit `ROUND_FINISHED`.

It returns `(events, final_state, usages)`, which `competition_service._run` persists.
The runner accepts a `should_stop` callable for cooperative cancellation.

### 5.1 Model resolution

`competition_service._make_resolver` builds a `resolve(model_ref) -> (provider, model)`
callable using `settings_service.get_role_defaults()` and the registry. A crew member's
effective model is: explicit `member.model` → role default → global default → env
`DEFAULT_PROVIDER`/`DEFAULT_MODEL`.

### 5.2 The referee and the verdict guard

`app/domain/referee.py` wraps an LLM provider/model/params. `apply_guard(blueprint,
parsed)` validates the `{accepted, score, explanation}` shape and clamps the score to
the `dialogue.scoring` bounds — so the referee is a real LLM that can never corrupt
state.

### 5.3 Interaction log

Dialogue events (`CREW_MESSAGE`, `ACTION_PROPOSED`, `REFEREE_VERDICT`) carry the full
trace in `payload_json`: prompt, parameters, raw + parsed response, tokens, model. This
is what the visualization and replay render.

### 5.4 Asynchronous runs (Redis + rq)

`competition_service.start_competition` sets `queued` and enqueues `run_competition_job`.
A worker (`flask --app run.py worker`) runs the job: `running` → `finished`/`failed`/
`cancelled`. `app/infrastructure/queue.py:enqueue` runs synchronously when no
`REDIS_URL` is set. The web UI polls `/api/competitions/<id>/events?after=N`.

---

## 6. Recipes

### 6.1 Add a new game template

Create a directory under `game_templates/` containing:

```text
my_game/
├── manifest.yaml      # game, competition, crew, referee, resources, dialogue
├── playground.yaml    # playground permissions
├── game.md rules.md scoring.md referee.md
├── agents/<role>.md   # one file per crew role
└── skills/<skill>.md
```

`manifest.yaml` must include `crew.roles` (exactly one `speaker: true`) and
`dialogue.actions`/`scoring`. Example:

```yaml
game: {id: my_game, name: My Game, version: 1.0.0, description: ""}
competition: {teams: 2, default_round_budget: 10, wall_clock_timeout_seconds: 600}
crew:
  roles:
    - {id: trainee, speak_order: 1, speaker: true, required: true}
    - {id: explorer, speak_order: 2, speaker: false, required: true}
referee: {enabled: true, role: referee, response_format: json}
resources: {team_token_budget: 50000, team_memory_budget: 12000, max_concurrent_agents: 2}
dialogue:
  actions: [{id: EXPLORE}, {id: COLLECT}]
  scoring:
    - {id: collect, kind: event, event: COLLECT, points: 1, probability: 0.5}
  win: highest_score
```

Load it via the UI (**Games → New My Game**) or `flask --app run.py seed`.

### 6.2 Add a new scoring rule kind

The referee guard (`app/domain/referee.py:clamp_score`) clamps scores to the
`dialogue.scoring` rules. Add a new `kind` by updating `clamp_score` and
`validate_blueprint` (`app/application/validation.py`).

### 6.3 Add a new LLM provider

OpenAI-compatible providers (including Ollama) need no code — add an entry to
`LLM_PROVIDERS`. For a new provider *type*, subclass `LLMProvider`
(`app/infrastructure/llm/base.py`), implement `complete(messages, **kwargs)`, and
register it in `app/infrastructure/llm/registry.py:build_registry`.

### 6.4 Add a data model + migration

Add the class to `app/models.py`, then:

```bash
flask --app run.py db migrate -m "add my_model"
flask --app run.py db upgrade
```

### 6.5 Add a new web page/module

Create a blueprint in `app/web/`, register it in `app/__init__.py:register_blueprints`,
add templates under `app/web/templates/`, and add a nav link in `base.html`.

### 6.6 Add a new event type + visualization handling

Add a constant to `app/domain/events.py`, emit it from `DialogueRunner`, and handle it
in `renderEvent` in `app/web/static/js/visualization.js`.

### 6.7 Add a CLI command

Use `@app.cli.command` in `app/__init__.py:register_cli` (see `create-user`).

---

## 7. Conventions and guardrails

- **Keep game logic out of `app/web`.** Routes call services; services call the domain.
- **Keep `app/domain` Flask-free.**
- **Validation is shared.** Add checks to `validation.py`; compiler and importer benefit
  automatically.
- **Determinism.** Outcomes derive from the seeded RNG, never `random`/time directly.
- **Referee is fenced.** Always apply `apply_guard` before mutating state.
- **Secrets.** Never write API keys or DB credentials into blueprints/Markdown; use env.
- **No student code execution.** Student content is Markdown/text/structured config.
- **Version everything.** Competitions reference immutable game versions.

---

## 8. Testing

- Integration tests live in `tests/test_app.py` (`tests/conftest.py` builds a temp-DB
  app and seeds it).
- Add tests for new models/migrations, scoring rules, dialogue behavior, matchmaking
  lifecycle, and routes.
- Because the `mock` provider is deterministic, you can assert exact event sequences.

```bash
pytest
pytest tests/test_app.py
pytest -k match
```

---

## 9. Configuration reference

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///instance/app.db` | SQLAlchemy URI |
| `POSTGRES_USER/PASSWORD/HOST/PORT/DB` | *empty* | Build `DATABASE_URL` when unset |
| `REDIS_URL` | *empty* | Redis URL (empty = synchronous runs) |
| `LLM_PROVIDERS` | *empty* | JSON list of providers `{id, type, base_url, api_key, models[]}` |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | `mock` / `mock-model` | Global fallback provider/model |
| `SEED_ON_START` | `false` | Docker entrypoint seeds on boot |
| `GAME_TEMPLATES_DIR` | `game_templates` | Seed template directory |
| `ADMIN_USERNAME/PASSWORD/EMAIL` | `admin`/`admin123`/… | First-boot admin (via `flask seed`) |
| `SECRET_KEY` | dev value | Session signing key |

---

## 10. Upgrading safely

1. Pin dependencies in `requirements.txt`; bump deliberately and re-run tests.
2. Migrate with `flask --app run.py db migrate` + `db upgrade`; commit the migration.
3. Back up the database before migrating a shared instance.
4. Keep game versions immutable.
5. Follow the layer rules in section 7.
