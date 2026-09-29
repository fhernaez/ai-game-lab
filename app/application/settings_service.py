"""Admin settings: per-provider model lists and the global default model."""

from flask import current_app

from ..extensions import db
from ..models import AppSetting

PROVIDER_MODELS_KEY = "provider_models"
DEFAULT_MODEL_KEY = "default_model"


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


def get_provider_models():
    saved = _get(PROVIDER_MODELS_KEY)
    if saved is not None:
        return saved
    env_models = {"mock": ["mock-model"]}
    for entry in current_app.config.get("LLM_PROVIDERS") or []:
        env_models[entry.get("id")] = entry.get("models") or []
    return env_models


def set_provider_models(mapping):
    _set(PROVIDER_MODELS_KEY, dict(mapping))


def get_default_model():
    return _get(DEFAULT_MODEL_KEY, "") or ""


def set_default_model(ref):
    _set(DEFAULT_MODEL_KEY, ref or "")
