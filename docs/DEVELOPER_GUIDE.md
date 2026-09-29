# AI Game Lab — Developer Guide

This guide explains how the application is structured and how to customize it with
precision, upgrade it safely, and add new modules and functionality.

It assumes you have read `STARTUP_GUIDE.md` and can run the app locally
(`flask --app run.py db upgrade`, `flask --app run.py seed`, `flask --app run.py run`).

---

## 1. Architecture at a glance

The application follows the four-layer model described in `../specs/ARCHITECTURE.md`.

```text
Browser (Jinja2 + HTMX + vanilla JS)
   |
   v
web/            Flask routes + templates + static assets  (no game rules here)
   |
   v
application/    workflow services / orchestration
   |
   v
domain/         game engine, referee, prompts, events     (no Flask imports)
   |
   v
infrastructure/ LLM provider registry, database (SQLAlchemy), Redis/rq queue
```

Key rules that keep the codebase healthy:

- **Domain layer is Flask-free.** `app/domain/*` imports nothing from Flask. This
  makes the game engine unit-testable and portable.
- **No game mechanics in routes.** The web layer never knows about "debate" or
  "team sports"; it delegates to services and the generic engine.
- **Structured configuration is authoritative.** The database stores a structured
  blueprint dict (`GameVersion.blueprint_json`); Markdown/YAML files are generated
  renders of it, not the source of truth.
- **Deterministic compiler.** The same blueprint always compiles to the same files
  (`sort_keys=True`, see `app/application/compiler_service.py`).
- **Round-trip.** The compiler (structured → files) and the importer (files →
  structured) share the same validation, so Technical-view edits are safe.

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
│   ├── __init__.py           # app factory + blueprint/CLI registration
│   ├── extensions.py         # db, login_manager, migrate
│   ├── models.py             # SQLAlchemy models (incl. AppSetting)
│   ├── worker.py             # (see `flask worker`) rq worker entrypoint
│   ├── web/                  # HTTP layer
│   │   ├── auth.py settings.py games.py playground.py
│   │   ├── competitions.py replay.py api.py
│   │   ├── templates/        # Jinja2 (base.html + per-area)
│   │   └── static/           # css/app.css, js/visualization.js
│   ├── application/          # services
│   │   ├── blueprint_service.py    # create/save/version games
│   │   ├── compiler_service.py     # blueprint -> files
│   │   ├── importer_service.py     # files -> blueprint (round-trip)
│   │   ├── validation.py           # shared validation rules
│   │   ├── agent_service.py        # default agent/team configs
│   │   ├── settings_service.py     # role-default provider/model + resolution
│   │   ├── competition_service.py  # create/enqueue/run competitions
│   │   └── seed.py                 # admin + template seeding
│   ├── domain/               # pure game logic
│   │   ├── engine.py         # GameEngine (per-agent provider resolver)
│   │   ├── referee.py        # deterministic validation + scoring
│   │   ├── prompts.py        # prompt assembly
│   │   └── events.py         # event types + constructors
│   └── infrastructure/
│       ├── queue.py          # Redis/rq wrapper (sync fallback)
│       └── llm/              # LLM provider registry
│           ├── base.py       # LLMProvider, LLMResult
│           ├── mock.py       # deterministic offline provider
│           ├── openai_compatible.py  # OpenAI / Ollama endpoints
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
cp .env.example .env        # adjust as needed
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
docker compose up -d --build          # db, redis, app, worker
docker compose logs -f app worker     # follow logs
docker compose exec app flask --app run.py create-user ...   # run CLI in the container
```

For a fast inner loop you can still run the app outside Docker with SQLite and
`REDIS_URL` unset (runs execute synchronously); use Docker when you need PostgreSQL,
Redis, or the async worker.

---

## 4. Core concept: the blueprint

A game is a Python dict stored in `GameVersion.blueprint_json`. Its top-level keys:

```text
game         id, name, version, description
competition  teams, turn_mode, action_timeout, duration {type, value}
teams        agents_per_team, roles [{id, count, required}]
referee      enabled, agent_template
resources    team_token_budget, team_memory_budget, max_concurrent_agents
engine       actions [...], scoring [...], win
playground   editable [...], locked [...]
markdown     game, rules, scoring, referee, agents {role: md}, skills {skill: md}
```

The `engine` block is the machine-readable runtime spec the generic engine reads.
`markdown` holds the human-readable instruction texts.

The blueprint is rendered to files by `app/application/compiler_service.py`
(`manifest.yaml`, `playground.yaml`, and the `*.md` files) and parsed back by
`app/application/importer_service.py`. Both sides call
`app/application/validation.py:validate_blueprint`, so a blueprint is valid
regardless of whether it came from the GUI or the Technical view.

---

## 5. The generic game engine

`app/domain/engine.py` is intentionally game-agnostic. It reads the blueprint's
`engine` block and drives a turn/round loop:

1. Emit `GAME_STARTED`.
2. For each iteration (`competition.duration.value`):
   - emit `TURN_STARTED`;
   - for each team: every agent emits an `AGENT_MESSAGE`, then one **declaring
     agent** declares a structured action, the referee validates it and resolves
     scoring (`ACTION_DECLARED` → `ACTION_ACCEPTED`/`ACTION_REJECTED` →
     `SCORE_CHANGED`/`STATE_CHANGED`);
   - emit `TURN_FINISHED`.
3. Emit `GAME_FINISHED`.

It returns `(events, final_state, usages)`, which `competition_service.py` persists.

### 5.1 Actions

Defined in `engine.actions`:

```yaml
engine:
  actions:
    - id: SHOOT
    - id: SUBMIT_ARGUMENT
      roles: [speaker]      # optional: restrict which role may declare this action
```

- `referee.allowed_actions_for(blueprint, role)` lists the actions a role may use.
- `referee.validate_action(blueprint, role, action)` performs the authoritative
  schema + permission check.
- The **declaring agent** is chosen by `GameEngine._declaring_agent`: if an action
  is restricted to a single role, that role's agent declares; otherwise the trainee
  (or the first agent) declares.

### 5.2 Scoring

Defined in `engine.scoring`. Two built-in kinds exist, both resolved in
`referee.resolve_scoring`:

- **`event`** — score when a specific action succeeds, with a probability:

  ```yaml
  - id: goal
    kind: event
    event: SHOOT
    points: 3
    probability: 0.4
  ```

- **`criteria`** — award points across named criteria (used by the debate template):

  ```yaml
  - id: debate_score
    kind: criteria
    criteria: [relevance, evidence, response, clarity, compliance]
    max: 5
  ```

`resolve_scoring` receives a seeded `random.Random` instance, so runs with the same
seed are reproducible (essential for replay and tests).

### 5.3 Prompt assembly

`app/domain/prompts.py` builds prompts from controlled sections (rules, role,
skills, team instructions, state, recent events, allowed actions). The engine resolves
each agent's provider/model and calls `provider.complete(...)`, then parses the
structured action out of the response. Keep this sectioned design: never bake
authoritative rules *only* into the prompt.

### 5.4 LLM providers, models, and role defaults

Providers come from the environment, not the database. `LLM_PROVIDERS` is a JSON list
of `{id, type, base_url, api_key, models[]}`; `mock` is always available.
`app/infrastructure/llm/registry.py` builds a `{id: ProviderSpec}` mapping and
`resolve_model(ref)` turns `"provider:model"` (or a bare model name, resolved against
`DEFAULT_PROVIDER`) into a `(provider, model)` pair.

The administrator can set a default model per AI role in **Settings → Role defaults**;
this is stored in the `AppSetting` table by `app/application/settings_service.py`.
The resolution order for an agent's model is:

1. the agent's explicit `model` (set in the Playground),
2. the role default,
3. the global default model,
4. the environment `DEFAULT_PROVIDER` / `DEFAULT_MODEL` fallback.

`competition_service._make_resolver` builds a `resolve(agent)` callable implementing
this order and passes it to `GameEngine`, so each agent can use a different provider
and model within a single run.

### 5.5 Asynchronous runs (Redis + rq)

`competition_service.enqueue_competition` sets the competition to `queued` and pushes
`run_competition_job` onto the `competitions` queue. A worker process
(`flask --app run.py worker`) executes the job: it sets `running`, runs the engine,
persists events/actions/usage, and sets `finished` (or `failed` with the error).

`app/infrastructure/queue.py:enqueue` falls back to running the job synchronously when
no `REDIS_URL` is configured, so local development and tests work without Redis. The
web UI polls `/api/competitions/<id>/events?after=N` while the status is
`queued`/`running`, which is what makes the visualization live.

---

## 6. Recipes

### 6.1 Add a new game template

Create a directory under `game_templates/` containing:

```text
my_game/
├── manifest.yaml      # game, competition, teams, referee, resources, engine
├── playground.yaml    # playground permissions
├── game.md rules.md scoring.md referee.md
├── agents/<role>.md   # one file per role id in teams.roles
└── skills/<skill>.md  # one file per referenced skill
```

`manifest.yaml` must include the `engine` block (actions + scoring). Example for a
simple turn-based game:

```yaml
game:
  id: my_game
  name: My Game
  version: 1.0.0
  description: A custom game.
competition:
  min_players: 2
  max_players: 2
  teams: 2
  turn_mode: sequential
  action_timeout_seconds: 30
  duration: {type: turns, value: 10}
teams:
  agents_per_team: 2
  roles:
    - {id: trainee, count: 1, required: true}
    - {id: explorer, count: 1, required: true}
referee: {enabled: true, agent_template: referee}
resources:
  team_token_budget: 50000
  team_memory_budget: 12000
  max_concurrent_agents: 2
engine:
  actions:
    - {id: EXPLORE}
    - {id: COLLECT}
  scoring:
    - {id: collect, kind: event, event: COLLECT, points: 1, probability: 0.5}
  win: highest_score
```

Then either create a game from it via the UI (**Games → New My Game**) or run
`flask --app run.py seed` to load it automatically (seeding is idempotent and skips
games that already exist by name).

No code changes are required for a template that only uses the built-in action and
scoring machinery.

### 6.2 Add a new scoring kind

Edit `referee.resolve_scoring` (`app/domain/referee.py`) to handle a new `kind`:

```python
elif kind == "threshold":
    if some_condition(rule, action_type, rng):
        earned = int(rule.get("points", 1))
        points += earned
        explanations.append(f"{rule.get('id')}: +{earned}")
```

Keep it deterministic (only use the passed `rng`). If the rule references actions,
also update `app/application/validation.py:validate_blueprint` so invalid references
are caught on import.

### 6.3 Add a new LLM provider

**OpenAI-compatible providers (including Ollama) need no code.** Add an entry to the
`LLM_PROVIDERS` environment variable:

```dotenv
LLM_PROVIDERS=[...,{"id":"myvendor","type":"openai","base_url":"https://api.myvendor.com/v1","api_key":"sk-...","models":["model-a","model-b"]}]
```

For a new provider *type*, subclass `LLMProvider` in `app/infrastructure/llm/`:

```python
from .base import LLMProvider, LLMResult

class MyProvider(LLMProvider):
    name = "myprovider"

    def complete(self, messages, **kwargs):
        # call the model, return LLMResult(content=..., tokens_input=..., ...)
        ...
```

Then register it in `app/infrastructure/llm/registry.py:build_registry` (add a
`provider_type` branch) and handle `resolve_model`/`models_for` as needed.

The engine only depends on `LLMProvider.complete(messages, **kwargs)` and
`LLMResult.parse_json()`, so a conforming provider works without touching the engine.

### 6.4 Add a data model + migration

1. Add the class to `app/models.py`.
2. Generate and apply a migration:

   ```bash
   flask --app run.py db migrate -m "add my_model"
   flask --app run.py db upgrade
   ```

3. Add a relationship from any other model if needed, and use `db.session` in the
   corresponding application service.

### 6.5 Add a new web page/module

1. Create a blueprint in `app/web/`, e.g. `app/web/leaderboard.py`:

   ```python
   from flask import Blueprint, render_template
   from flask_login import login_required

   bp = Blueprint("leaderboard", __name__, url_prefix="/leaderboard")

   @bp.route("")
   @login_required
   def index():
       return render_template("leaderboard/index.html")
   ```

2. Register it in `app/__init__.py:register_blueprints`:

   ```python
   from .web.leaderboard import bp as leaderboard_bp
   app.register_blueprint(leaderboard_bp)
   ```

3. Add templates under `app/web/templates/leaderboard/` and static assets under
   `app/web/static/`. Extend `base.html` for consistent chrome and add a nav link.

### 6.6 Add a new event type + visualization handling

1. Add a constant to `app/domain/events.py` and emit it from `GameEngine` or a new
   service.
2. Handle it in the visualizer's `renderEvent` in
   `app/web/static/js/visualization.js` (draw an edge, pulse a node, or update the
   scoreboard). Existing event types show the pattern.

### 6.7 Add a CLI command

Use Flask's CLI in `app/__init__.py:register_cli`:

```python
@app.cli.command("my-command")
def my_command():
    ...
```

`click` is already a dependency, so `@click.argument` / `@click.option` work out of
the box (see the existing `create-user` command).

---

## 7. Conventions and guardrails

- **Keep game logic out of `app/web`.** Routes call services; services call the
  domain layer.
- **Keep `app/domain` Flask-free.** Import nothing from `flask` there.
- **Validation is shared.** Add new checks to `validation.py`, and both the compiler
  and importer benefit automatically.
- **Determinism.** Anything that influences a competition's outcome must derive from
  the seeded RNG, never `random`/time directly.
- **Secrets.** Never write API keys or database credentials into blueprints, Markdown,
  or the database. Use environment variables (see `.env.example`).
- **No student code execution.** Student-authored content is Markdown/text/structured
  config only. The Technical view must never become a path to running Python or shell
  commands (see `SECURITY_AND_SANDBOX.md` in `../specs/`).
- **Version everything.** Changing a game definition creates a new `GameVersion`;
  competitions reference an immutable version, so history never changes.

---

## 8. Testing

- Integration tests live in `tests/test_app.py` and use the fixtures in
  `tests/conftest.py`.
- Add tests for any new: model/migration, service, scoring rule, event, or route.
- Because the engine is deterministic, you can assert exact event sequences for a
  fixed seed when testing game logic.

```bash
pytest                     # full suite
pytest tests/test_app.py   # single file
pytest -k roundtrip        # by keyword
```

---

## 9. Configuration reference

All settings come from environment variables (loaded from `.env` by `config.py`).

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///instance/app.db` | SQLAlchemy URI |
| `POSTGRES_USER/PASSWORD/HOST/PORT/DB` | *empty* | Build `DATABASE_URL` when it is unset |
| `REDIS_URL` | *empty* | Redis URL (empty = synchronous runs) |
| `LLM_PROVIDERS` | *empty* | JSON list of providers `{id, type, base_url, api_key, models[]}` |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | `mock` / `mock-model` | Global fallback provider/model |
| `SEED_ON_START` | `false` | Docker entrypoint seeds on boot |
| `GAME_TEMPLATES_DIR` | `game_templates` | Seed template directory |
| `ADMIN_USERNAME/PASSWORD/EMAIL` | `admin`/`admin123`/… | First-boot admin (via `flask seed`) |
| `SECRET_KEY` | dev value | Session signing key |

---

## 10. Upgrading safely

1. **Pin dependencies** in `requirements.txt`; bump deliberately and re-run tests.
2. **Migrate the schema** with `flask --app run.py db migrate` + `db upgrade`; commit
   the generated migration file. Never hand-edit applied migrations.
3. **Back up the database** before running migrations against a shared instance.
4. **Keep game versions immutable** — extend templates, don't silently change old
   ones, so historical competitions remain replayable.
5. **Follow the layer rules** in section 7 so the generic engine and the web layer
   stay independent as the app grows.
