# AI Game Lab — V3 (Beach Volleyball)

Educational, browser-based, multi-user Flask platform for learning how large language
models work, through a **single, deeply-simulated game: beach volleyball**.

See `specs/` (especially `VOLLEYBALL_SPEC.md`) for the full specification.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # optional: edit for PostgreSQL / Ollama

flask --app run.py db upgrade   # create / migrate the database schema
flask --app run.py seed         # create the admin user
flask --app run.py run
```

Then open http://localhost:5000 and log in as `admin` / `admin123`
(override with `ADMIN_USERNAME` / `ADMIN_PASSWORD`).

### Docker quick start

```bash
cp .env.example .env
docker compose up -d --build
```

Full setup and usage instructions:

- `docs/STARTUP_GUIDE.md` — installation, database, Ollama, environment, Docker.
- `docs/USER_GUIDE.md` — matchmaking, team configuration, the match view, history.
- `docs/DEVELOPER_GUIDE.md` — architecture and how to customize/extend.

## Features

- **Beach volleyball engine**: a full match (best of 3 sets, 21/15 win-by-2) with
  stochastic serve/flight/defense physics and volleyball rules (faults, possession,
  court switch).
- **Athlete attributes**: 7 skills per player (Vertical Leap, Sand Speed, Dig & Serve
  Receive, Set Precision, Sniper Vision, Power Control, Spike Power) set with 1–10
  sliders, with a point-buy economy (Easy/Medium/Hard) and preset archetypes.
- **LLM mind**: each player is an LLM (model from `LLM_PROVIDERS` + temperature, top-p,
  penalties, …) that decides the tactics; the attributes decide whether it works.
- **Multi-user matches**: invite an online player, accept, each configures their 2-player
  team, both ready, the match auto-starts.
- **Graphical simulation**: an independent SVG module animating the players and ball on
  the court.
- **Interaction log**: prompt, model, parameters, raw + parsed decision, attributes, and
  physics outcome for every play.
- **Match history**: every match persisted and browsable.
- **User administration**: admins manage accounts (create/role/delete).

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///instance/app.db` | SQLAlchemy URI |
| `POSTGRES_USER/PASSWORD/HOST/PORT/DB` | *empty* | Build `DATABASE_URL` when unset |
| `REDIS_URL` | *empty* | Redis URL (empty = synchronous runs) |
| `LLM_PROVIDERS` | *empty* | JSON list of providers `{id, type, base_url, api_key, models[]}` |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | `mock` / `mock-model` | Global fallback provider/model |
| `SEED_ON_START` | `false` | Docker entrypoint seeds on boot |

## CLI commands

| Command | Purpose |
| --- | --- |
| `flask db upgrade` | Create / migrate the database schema |
| `flask seed` | Create the admin user |
| `flask create-user USER EMAIL ROLE` | Create a user |
| `flask worker` | Start a background worker for queued matches |

## Tests

```bash
pip install pytest
pytest
```

## Structure

```
app/
├── web/            # routes, templates, static (volleyball_court.js)
├── application/    # matchmaking, presence, team, match, settings services
├── domain/volleyball/   # state, rules, physics, attributes, engine, decisions
├── infrastructure/ # LLM provider registry, queue (Redis/rq)
└── models.py       # Match, Team, Player, Event, User, AppSetting
```
