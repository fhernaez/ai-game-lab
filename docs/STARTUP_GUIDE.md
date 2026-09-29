# AI Game Lab — Startup Guide

This guide walks an administrator or teacher through installing AI Game Lab,
connecting it to an external database, connecting it to a local Ollama server,
and configuring the environment. It ends with the teacher's first-run checklist:
create a first game definition and set up user accounts.

---

## 1. Prerequisites

- **Python 3.10+** (developed against 3.14).
- `pip` and `venv`.
- (Optional) **PostgreSQL 14+** if you want an external database.
- (Optional) **Ollama** running locally or on a server, for real model-driven agents.

---

## 2. Install the application

```bash
cd AI-Edu-game-lab-app-v1

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

The PostgreSQL driver (`psycopg[binary]`), Redis client, and task queue (`rq`) are
already included in `requirements.txt`.

---

## 3. Environment configuration

The application reads its configuration from environment variables. The simplest
way to set them is a `.env` file in the project root (it is loaded automatically).

```bash
cp .env.example .env
```

Then edit `.env`. The key settings are described below.

### 3.1 Connect to an external database

Set `DATABASE_URL` to your PostgreSQL connection string:

```dotenv
DATABASE_URL=postgresql+psycopg://ai_game_lab:strongpassword@dbhost.example.com:5432/ai_game_lab
```

The format is:

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
```

Notes:

- The database itself must already exist. Create it first, for example:

  ```bash
  createdb ai_game_lab
  ```

- To keep using the built-in SQLite database (good for a quick local trial), use:

  ```dotenv
  DATABASE_URL=sqlite:///instance/app.db
  ```

- The driver must be installed (`pip install "psycopg[binary]"`, see section 2).

### 3.2 Initialize the new database

The database schema is managed with Alembic (Flask-Migrate). Run the migrations to
create or upgrade the tables:

```bash
flask --app run.py db upgrade
```

Then load the initial data (admin user and the two seed game templates):

```bash
flask --app run.py seed
```

Run these two commands whenever you point the application at a fresh database.
`db upgrade` is idempotent and safe to re-run after code updates.

### 3.3 Configure LLM providers (multi-provider, multi-model)

The application supports any number of LLM providers, each offering one or more
models. Providers are configured with the `LLM_PROVIDERS` environment variable (a
JSON list). The `mock` provider is always available offline.

Each provider entry has:

| Field | Meaning |
| --- | --- |
| `id` | Unique name, used in `provider:model` references. |
| `type` | `"openai"` (OpenAI-compatible; Ollama included) or `"mock"`. |
| `base_url` | API base URL (for `openai` type). |
| `api_key` | API key (Ollama ignores it; use any non-empty value). |
| `models` | List of model names offered by this provider. |

#### Ollama

1. Make sure Ollama is running and that a model is pulled:

   ```bash
   ollama serve            # if not already running
   ollama pull llama3.2    # or another model, e.g. qwen2.5, mistral
   ```

2. Register it in `.env` (Ollama exposes an OpenAI-compatible API at
   `http://localhost:11434/v1`):

   ```dotenv
   LLM_PROVIDERS=[{"id":"ollama","type":"openai","base_url":"http://localhost:11434/v1","api_key":"ollama","models":["llama3.2","qwen2.5"]}]
   ```

#### External OpenAI-compatible service

Add a second entry for any OpenAI-compatible vendor:

```dotenv
LLM_PROVIDERS=[{"id":"ollama","type":"openai","base_url":"http://localhost:11434/v1","api_key":"ollama","models":["llama3.2"]},{"id":"openai","type":"openai","base_url":"https://api.openai.com/v1","api_key":"sk-...","models":["gpt-4o-mini","gpt-4o"]}]
```

#### Global default

`DEFAULT_PROVIDER` / `DEFAULT_MODEL` select the fallback used when a role or agent
has no explicit model:

```dotenv
DEFAULT_PROVIDER=ollama
DEFAULT_MODEL=llama3.2
```

To run fully offline with the deterministic built-in provider, use
`DEFAULT_PROVIDER=mock` / `DEFAULT_MODEL=mock-model` (the default).

> The **model lists per provider** and the **default provider + model per AI role** are
> managed from the web UI (**Settings**), stored in the database. On first use they are
> seeded from the `models` lists in `LLM_PROVIDERS`.
>
> The `mock` provider is always available offline: it needs no URL or API key and
> produces deterministic dialogue, so it is used for demos and testing.

### 3.4 Other settings

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Session signing key. Use a long random value in production. |
| `DATABASE_URL` | SQLAlchemy URI (or set the discrete `POSTGRES_*` variables). |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` | Build `DATABASE_URL` when it is unset. |
| `REDIS_URL` | Redis URL for async competition runs (empty = synchronous). |
| `LLM_PROVIDERS` | JSON list of providers `{id, type, base_url, api_key, models[]}`. |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | Global fallback provider/model. |
| `SEED_ON_START` | When `true`, the Docker entrypoint runs `flask seed` on boot. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` | First-boot administrator created by `flask seed`. |
| `GAME_TEMPLATES_DIR` | Directory containing the seed game templates (normally leave unchanged). |

### 3.5 Docker deployment

A complete `docker-compose.yml` is provided (PostgreSQL, Redis, web app, and a
background worker).

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, POSTGRES_PASSWORD, and LLM_PROVIDERS

docker compose up -d --build
```

- The web app runs on `http://localhost:5000`.
- On first boot the entrypoint runs `flask db upgrade` and (when
  `SEED_ON_START=true`) `flask seed`.
- Competition runs are processed asynchronously by the `worker` service using Redis;
  the graphical view polls live while a run progresses.

To include Ollama as a container:

```bash
docker compose --profile ollama up -d ollama
```

Then point `LLM_PROVIDERS` at `http://ollama:11434/v1` (the compose service name) and
pull a model inside the container:

```bash
docker compose exec ollama ollama pull llama3.2
```

---

## 4. Start the server

```bash
flask --app run.py run --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000` and log in with the administrator credentials created
by `flask seed` (default `admin` / `admin123` — change these in `.env` before first
run, or with `create-user`).

For production, run behind a WSGI server:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

---

## 5. Teacher's first-run checklist

### 5.1 Configure the environment

Confirm the following before sharing the application with students:

- [ ] `.env` points at the correct `DATABASE_URL` (or `POSTGRES_*` variables).
- [ ] `flask --app run.py db upgrade` has created the schema.
- [ ] `flask --app run.py seed` has loaded the seed games and admin user.
- [ ] `LLM_PROVIDERS` lists the Ollama and/or external providers, and
      `DEFAULT_PROVIDER` / `DEFAULT_MODEL` are set.
- [ ] `SECRET_KEY` has been changed from the default.

### 5.2 Create your first game definition

1. Log in as `admin` (or a teacher account).
2. Open **Games**.
3. Click **New Ai Debate Challenge** (or **New Ai Team Sports Challenge**) to create
   a game from a template.
4. Click **Design** on the new game.
5. Adjust the identity, execution budget (rounds), crew roles and speak order, resources,
   referee, playground permissions, and the plain-language instructions (game, rules,
   scoring, referee, crew-member, and skill texts).
6. Click **Save version**.
7. Optionally open **Technical view** to inspect or fine-tune the generated
   `manifest.yaml`, `playground.yaml`, and Markdown files.

### 5.3 Set up users

Admins can manage users from the web UI: log in as `admin`, open **Users**, and create
accounts (username, email, role, password), change roles, or delete users.

You can also create accounts from the command line:

```bash
flask --app run.py create-user mrsmith mrsmith@school.edu teacher
flask --app run.py create-user alice alice@school.edu student
```

You will be prompted to enter (and confirm) a password for each user. Roles are
`admin`, `teacher`, or `student`.

Students can also self-register from the login page via **Register** (these accounts
are created with the `student` role). To run a multi-player match, create at least two
student accounts, then invite one from the other in **Matchmaking**.

---

## 6. Troubleshooting

- **`flask db upgrade` fails to connect** — check `DATABASE_URL`, that the database
  exists, that the host/port are reachable, and that `psycopg` is installed.
- **Agents behave randomly / no LLM output** — confirm the provider is reachable
  (e.g. Ollama running, model pulled) and that `LLM_PROVIDERS` / `DEFAULT_PROVIDER` /
  `DEFAULT_MODEL` are correct. Test with `DEFAULT_PROVIDER=mock` to isolate the
  problem.
- **Runs stay "queued" in Docker** — check `docker compose ps` to confirm the
  `worker` service is running and `docker compose logs worker` for errors; confirm
  `REDIS_URL` points at the `redis` service.
- **`flask seed` reports missing tables** — run `flask --app run.py db upgrade` first.
