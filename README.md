# AI Game Lab — V1 Application

Educational, browser-based Flask platform for secondary-school students to learn AI
concepts by designing and playing games powered by teams of AI agents.

See `../specs/` for the full specification.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # optional: edit for PostgreSQL / Ollama

flask --app run.py db upgrade   # create / migrate the database schema
flask --app run.py seed         # create the admin user + seed game templates
flask --app run.py run
```

Then open http://localhost:5000 and log in as `admin` / `admin123`
(override with `ADMIN_USERNAME` / `ADMIN_PASSWORD`).

### Docker quick start

```bash
cp .env.example .env       # set POSTGRES_PASSWORD, LLM_PROVIDERS, SECRET_KEY, ...
docker compose up -d --build
```

This starts PostgreSQL, Redis, the web app, and a background worker (migrations and
the initial seed run automatically on first boot). Optionally add Ollama:

```bash
docker compose --profile ollama up -d ollama
```

Full setup and usage instructions:

- `docs/STARTUP_GUIDE.md` — installation, external database, Ollama, environment
  configuration, Docker deployment, first game definition, and user management.
- `docs/USER_GUIDE.md` — how teachers and students use the Game Designer,
  Playground, Technical view, competitions, and replay.
- `docs/DEVELOPER_GUIDE.md` — architecture, and how to customize, upgrade, and add
  new modules (game templates, scoring rules, LLM providers, models, pages, events).

## Features

- **Game Designer**: create games from templates, configure through a friendly GUI,
  and version every change.
- **Technical view**: always-available toggle that renders the generated
  `manifest.yaml`, `playground.yaml`, and Markdown instruction files, and lets
  advanced students edit them (YAML/JSON are validated and reconciled; Markdown is
  stored verbatim).
- **Playground**: configure teams and agents, distribute tokens and memory, and run
  simulations.
- **Graphical execution view**: the default run view animates agent interaction —
  messages, declared actions, referee decisions, and score changes — as a node/edge
  diagram driven by the event stream.
- **Replay**: full event timeline, structured actions, and resource usage.
- **Multi-provider / multi-model LLM**: configure any number of OpenAI-compatible
  providers (including Ollama), each with its own models; the administrator sets a
  default provider + model per AI role.
- **Async runs**: competitions are executed by a background worker (Redis + rq), so
  the graphical view is live while a run progresses.

## Configuration

Environment variables (see `config.py` and the `.env.example` template):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///instance/app.db` | SQLAlchemy URI (PostgreSQL supported) |
| `POSTGRES_USER/PASSWORD/HOST/PORT/DB` | *empty* | Build `DATABASE_URL` when it is unset |
| `REDIS_URL` | *empty* | Redis URL for async runs (empty = synchronous) |
| `LLM_PROVIDERS` | *empty* | JSON list of providers `{id, type, base_url, api_key, models[]}` |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | `mock` / `mock-model` | Global fallback provider/model |
| `SEED_ON_START` | `false` | Docker entrypoint seeds on first boot |

The `mock` provider runs the full runtime deterministically without an API key.

## CLI commands

| Command | Purpose |
| --- | --- |
| `flask db upgrade` | Create / migrate the database schema |
| `flask seed` | Create the admin user + seed game templates |
| `flask create-user USER EMAIL ROLE` | Create a user (`admin` / `teacher` / `student`) |
| `flask worker` | Start a background worker for queued competition runs |

## Tests

```bash
pip install pytest
pytest
```

## Structure

```
app/
├── web/            # HTTP routes, templates, static assets
├── application/    # services: blueprint, compiler/importer, competition, settings, seed
├── domain/         # game engine, referee, prompts, events (no Flask)
├── infrastructure/ # LLM provider registry, queue (Redis/rq)
└── models.py       # SQLAlchemy data model
game_templates/     # seed templates (debate, team_sports)
docker/             # Dockerfile entrypoint
docker-compose.yml  # db + redis + app + worker (+ ollama profile)
```
