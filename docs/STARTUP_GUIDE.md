# AI Game Lab — Startup Guide (Beach Volleyball)

This guide walks an administrator through installing AI Game Lab V3, connecting an
external database, connecting Ollama / OpenAI-compatible providers, and deploying with
Docker. It ends with the teacher's first-run checklist.

---

## 1. Prerequisites

- Python 3.10+ (developed against 3.14), `pip`, `venv`.
- (Optional) PostgreSQL 14+.
- (Optional) Ollama or any OpenAI-compatible endpoint.

## 2. Install

```bash
cd AI-Edu-game-lab-app-v1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The PostgreSQL driver, Redis client, and task queue (`rq`) are already included.

## 3. Environment configuration

```bash
cp .env.example .env
```

### 3.1 External database

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/ai_game_lab_db
```

(or set the discrete `POSTGRES_USER/PASSWORD/HOST/PORT/DB` variables). The database must
exist first (`createdb ai_game_lab_db`).

### 3.2 Initialize the database

```bash
flask --app run.py db upgrade
flask --app run.py seed
```

### 3.3 LLM providers (multi-provider)

Providers (id, type, base_url, api_key) are defined in `LLM_PROVIDERS`:

```dotenv
LLM_PROVIDERS=[{"id":"ollama","type":"openai","base_url":"http://localhost:11434/v1","api_key":"ollama","models":["llama3.2"]},{"id":"openai","type":"openai","base_url":"https://api.openai.com/v1","api_key":"sk-...","models":["gpt-4o-mini"]}]
```

The **model list per provider** and the **global default model** are managed from the web
UI (**Settings**), seeded from these env values. The `mock` provider is always available
offline (deterministic, for testing) and needs no key.

### 3.4 Other settings

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Session signing key (long random value). |
| `REDIS_URL` | Redis URL for async matches (empty = synchronous). |
| `DEFAULT_PROVIDER` / `DEFAULT_MODEL` | Global fallback provider/model. |
| `SEED_ON_START` | Docker entrypoint seeds on boot. |
| `ADMIN_USERNAME/PASSWORD/EMAIL` | First-boot admin. |

### 3.5 Docker

```bash
docker compose up -d --build
# optional Ollama:
docker compose --profile ollama up -d ollama
```

## 4. Start

```bash
flask --app run.py run --host 0.0.0.0 --port 5000
# production:
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

Log in as `admin` / `admin123`.

## 5. Teacher's first-run checklist

1. Set `.env` (database, `LLM_PROVIDERS`, `SECRET_KEY`).
2. `flask db upgrade` + `flask seed`.
3. Log in as `admin`, open **Users**, and create at least two student accounts.
4. Have two students log in and create/accept a match to test the flow.

## 6. Troubleshooting

- **`flask db upgrade` fails** — check `DATABASE_URL` and that the DB exists and `psycopg`
  is installed.
- **Agents produce random/empty decisions** — check `LLM_PROVIDERS` / `DEFAULT_PROVIDER` /
  `DEFAULT_MODEL`; test with `DEFAULT_PROVIDER=mock`.
- **Matches stay `queued`** — confirm the `worker` service is running and `REDIS_URL`
  points at Redis.
- **Redis overcommit warning** — benign; run `sysctl vm.overcommit_memory=1` on the Docker
  host to silence it.
