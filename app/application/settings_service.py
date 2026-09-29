"""Admin settings: role defaults, global default model, and per-provider model lists."""

from flask import current_app

from ..extensions import db
from ..models import AppSetting, GameVersion

ROLE_DEFAULTS_KEY = "role_defaults"
DEFAULT_MODEL_KEY = "default_model"
PROVIDER_MODELS_KEY = "provider_models"


def _get(key, default=None):
    setting = AppSetting.query.filter_by(key=key).first()
    return setting.value if setting else default


def _set(key, value):
    setting = AppSetting.query.filter_by(key=key).first()
    if setting is None:
        setting = AppSetting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    db.session.commit()


def get_role_defaults():
    return _get(ROLE_DEFAULTS_KEY, {}) or {}


def set_role_defaults(mapping):
    _set(ROLE_DEFAULTS_KEY, dict(mapping))


def get_default_model():
    return _get(DEFAULT_MODEL_KEY, "") or ""


def set_default_model(ref):
    _set(DEFAULT_MODEL_KEY, ref or "")


def get_provider_models():
    """{provider_id: [models]}, seeded from env LLM_PROVIDERS on first use."""
    saved = _get(PROVIDER_MODELS_KEY)
    if saved is not None:
        return saved
    env_models = {"mock": ["mock-model"]}
    for entry in current_app.config.get("LLM_PROVIDERS") or []:
        env_models[entry.get("id")] = entry.get("models") or []
    return env_models


def set_provider_models(mapping):
    _set(PROVIDER_MODELS_KEY, dict(mapping))


def available_roles():
    """Union of crew role ids across all game versions."""
    roles = set()
    for version in GameVersion.query.all():
        blueprint = version.blueprint_json or {}
        for role in (blueprint.get("crew") or {}).get("roles", []):
            if role.get("id"):
                roles.add(role["id"])
    return sorted(roles)


def resolve_agent_model(role, explicit_model):
    """Effective model reference for a crew member."""
    if explicit_model:
        return explicit_model
    role_defaults = get_role_defaults()
    if role in role_defaults and role_defaults[role]:
        return role_defaults[role]
    return get_default_model() or None
