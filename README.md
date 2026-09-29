# AI Game Lab — V2 Application

Educational, browser-based, multi-user Flask platform for secondary-school students to
learn how large language models work — by pitting **crews of LLM models** against each
other in games where **the game is the dialogue itself**.

See `specs/` for the full specification.

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
- `docs/USER_GUIDE.md` — how teachers and students design games, configure crews,
  run multi-player matches, and read the interaction log.
- `docs/DEVELOPER_GUIDE.md` — architecture, and how to customize, upgrade, and add
  new modules (game templates, scoring rules, LLM providers, models, pages, events).

## Features

- **Crew dialogue engine**: each match is a bounded `speak → act → referee` dialogue
  between two crews of LLM models and a referee model. The result emerges from the
  dialogue.
- **Full model-parameter control**: configure model, temperature, max tokens, top-p,
  frequency/presence penalties, stop sequences, system prompt, and response format for
  every crew member.
- **LLM referee**: the referee is a real model returning a structured verdict; a
  deterministic guard validates and clamps its score to the rules.
- **Multi-user matchmaking**: log in, invite an online player, accept, each configures
  their own crew, both ready up, and the game auto-starts (1v1).
- **Interaction log**: the pedagogical trace — prompt, parameters, raw + parsed
  response, tokens, and timing — recorded for every dialogue message.
- **Graphical view + replay**: a node/edge diagram animates the dialogue; the event
  timeline shows the raw record.
- **Game Designer + Technical view**: create/version games, and edit the generated
  Markdown/YAML/JSON with round-trip validation.
- **Multi-provider / multi-model LLM**: providers are env-defined (`LLM_PROVIDERS`);
  model lists and per-role defaults are managed in Settings.

## Configuration

Environment variables (see `config.py` and `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///instance/app.db` | SQLAlchemy URI (PostgreSQL supported) |
| `POSTGRES_USER/PASSWORD/HOST/PORT/DB` | *empty* | Build `DATABASE_URL` when it is unset |
| `REDIS_URL` | *empty* | Redis URL for async runs (empty = synchronous) |
| `LLM_PROVIDERS` | *empty* | JSON list of providers `{id, type, base_url, api_key, models[]}` |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | `mock` / `mock-model` | Global fallback provider/model |
| `SEED_ON_START` | `false` | Docker entrypoint seeds on first boot |

The `mock` provider runs the full dialogue deterministically without an API key.

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
├── application/    # services: blueprint, compiler/importer, matchmaking, presence,
│                   #   crew, competition, settings, seed
├── domain/         # crew, dialogue runner, referee+guard, prompts, events (no Flask)
├── infrastructure/ # LLM provider registry, queue (Redis/rq)
└── models.py       # SQLAlchemy data model
game_templates/     # seed templates (debate, team_sports)
docker/             # Dockerfile entrypoint
docker-compose.yml  # db + redis + app + worker (+ ollama profile)
```
