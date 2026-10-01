# AI Game Lab — Beach Volleyball

**Learn how AI thinks, one rally at a time.**

A friendly, open-source, browser-based platform where students build their own
AI beach-volleyball teams, watch them play, and — most importantly — understand
*why* they play the way they do. Through a single, deeply-simulated game, students
discover how large language models actually work: the **brain** (the LLM), the
**body** (the athlete's attributes), and the **core** (the rules and physics).

---

## Why this project (our goals)

- **Teach AI by doing, not just reading.** Students configure the *mind* and the
  *body* of each player and see the consequences instantly on the court.
- **Make AI transparent.** Every decision is logged with its prompt, model,
  parameters, and outcome, so there are no black boxes.
- **Build intuition for the new AI era.** Students learn concepts like prompts,
  tools, skills, sensors, model parameters, and deterministic cores — the same ideas
  behind real agentic systems.
- **Keep it accessible.** It runs in a browser, works offline with a mock model, and
  needs nothing more than Python to start.

> This project is a contribution to the community to help young people understand
> and get involved with AI — theory and practice — and to develop the strengths
> they will need for the new AI era.

---

## What is it?

A multi-user **Flask** application that simulates beach-volleyball matches between
teams of AI players. Each player is an LLM that decides *what* to do, paired with a
small deterministic body that decides *whether it works*. A deterministic referee
applies the rules and physics, so every point can be explained and reproduced.

See the `specs/` folder (especially `specs/VOLLEYBALL_SPEC.md`) for the full
specification.

---

## Features

- **A real beach-volleyball engine** — best of three sets, win-by-2, faults
  (net, out, net touch, illegal attack, four touches), court switching, and a seeded
  deterministic core so matches are reproducible.
- **Brain / body / core architecture** — an LLM mind, 7 athlete attributes, and a
  deterministic referee; the clean separation is the whole point of the lesson.
- **Message-driven rallies** — every agent explains its decision in natural language,
  and those messages are shared to the rest of the rally as context.
- **Point-buy economy** — 7 skills (Vertical Leap, Sand Speed, Dig & Serve Receive,
  Set Precision, Sniper Vision, Power Control, Spike Power) with Easy/Medium/Hard
  budgets, preset **archetypes**, and preset **strategies** (Aggressive / Defensive /
  Neutral) that administrators can extend.
- **Multi-provider LLMs** — Ollama, any OpenAI-compatible endpoint, or an offline
  mock model; every agent picks its own model and parameters.
- **A living graphical simulation** — a 2.5D perspective court with animated humanoid
  players (front/back views, mirrored to face the action), a ball with shadow and
  trail, autoplay, and play/pause/scrub/speed controls.
- **Full interaction log** — prompt, model, parameters, raw + parsed decision,
  attributes, and the physics outcome of every touch.
- **Match history**, **multi-user matchmaking**, and **admin tools** for users,
  core files (rules / physics / referee), and strategy presets.

---

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

### Docker

```bash
cp .env.example .env
docker compose up -d --build
```

More details:

- `docs/STARTUP_GUIDE.md` — installation, database, Ollama, environment, Docker.
- `docs/USER_GUIDE.md` — matchmaking, team configuration, the match view, history.
- `docs/DEVELOPER_GUIDE.md` — architecture and how to customize and extend.

---

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

---

## Want to help? Collaborators are very welcome!

This is a living educational project, and there is plenty of room to contribute:

- **Educators** — classroom guides, lesson plans, or new games and exercises.
- **Developers** — frontend polish, better simulation, more LLM providers, tests.
- **AI enthusiasts** — prompt engineering, agent strategies, evaluation ideas.
- **Designers** — player sprites, court visuals, UX improvements.

Found a bug or have an idea? Open an issue or send a pull request. We review
contributions with care and credit every collaborator.

---

## About us — DOMAH SA

This project is created and maintained by **DOMAH SA**.

At Domah we specialize in comprehensive **customized software development focused on
AI applied to process optimization**. We also integrate **IoT, domotics, and automation
solutions**, enhancing productivity while minimizing environmental impact through
expert management and engineering.

We build this game as our way of giving back: a tool for young people to understand
and get involved with AI, both in theory and in practice.

Website: [domah.com.ar](https://domah.com.ar)

### Contact

- Email: [ingenieria@domah.com.ar](mailto:ingenieria@domah.com.ar)
- Phone / WhatsApp: +54 9 11 5958 5257

---

## Project structure

```
app/
├── web/            # routes, templates, static (simulation + player sprites)
├── application/    # matchmaking, presence, team, match, settings services
├── domain/volleyball/   # brain/, body/, core/ (rules, physics, world) + engine
├── infrastructure/ # LLM provider registry, queue (Redis/rq)
└── models.py       # Match, Team, Player, Event, User, AppSetting
```

Happy rallying — and welcome to the new AI era.
