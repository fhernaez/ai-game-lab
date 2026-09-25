import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from a .env file in the project root, if present.
load_dotenv(BASE_DIR / ".env")


def _parse_llm_providers(raw):
    """Parse the LLM_PROVIDERS JSON env var into a list of provider dicts."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM_PROVIDERS must be valid JSON.") from exc
    if not isinstance(data, list):
        raise RuntimeError("LLM_PROVIDERS must be a JSON list of provider objects.")
    return data


def _database_uri():
    """Build the SQLAlchemy URI from DATABASE_URL or discrete POSTGRES_* vars."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    if os.environ.get("POSTGRES_USER"):
        user = os.environ["POSTGRES_USER"]
        password = os.environ.get("POSTGRES_PASSWORD", "")
        host = os.environ.get("POSTGRES_HOST", "db")
        port = os.environ.get("POSTGRES_PORT", "5432")
        dbname = os.environ.get("POSTGRES_DB", "ai_game_lab")
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
    return "sqlite:///" + str(BASE_DIR / "instance" / "app.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get("REDIS_URL", "")
    RQ_REDIS_URL = os.environ.get("RQ_REDIS_URL", "") or REDIS_URL

    # Multi-provider LLM registry (see .env.example). Each entry:
    #   {"id", "type" ("openai"|"mock"), "base_url", "api_key", "models": [...]}
    LLM_PROVIDERS = _parse_llm_providers(os.environ.get("LLM_PROVIDERS", ""))

    # Global default provider/model (fallback for bare model names and roles
    # without an explicit default).
    DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "mock")
    DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "mock-model")

    # Legacy single-provider variables (deprecated; kept for backward
    # compatibility with the pre-registry configuration).
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mock")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "mock-model")

    GAME_TEMPLATES_DIR = os.environ.get(
        "GAME_TEMPLATES_DIR", str(BASE_DIR / "game_templates")
    )

    # Seed administrator credentials (first boot only).
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

    # When true, the container entrypoint runs `flask seed` after migrations.
    SEED_ON_START = os.environ.get("SEED_ON_START", "false").lower() in (
        "1",
        "true",
        "yes",
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    REDIS_URL = ""
    RQ_REDIS_URL = ""
