"""Admin settings: per-provider model lists, the global default model, and the core files."""

from flask import current_app

from ..domain.volleyball.core import defaults
from ..extensions import db
from ..models import AppSetting

PROVIDER_MODELS_KEY = "provider_models"
DEFAULT_MODEL_KEY = "default_model"
CORE_RULES_KEY = "core_rules"
CORE_PHYSICS_KEY = "core_physics"
CORE_REFEREE_KEY = "core_referee"


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


def _group_overrides():
    """Return {group: {knob: value}} from the two core override settings."""
    rules_ov = _get(CORE_RULES_KEY, {}) or {}
    physics_ov = _get(CORE_PHYSICS_KEY, {}) or {}
    return {"rules": rules_ov, "physics": physics_ov}


def get_core_overrides():
    """Flat dict of the admin's core overrides (validated/clamped)."""
    grouped = _group_overrides()
    overrides = {}
    for group in ("rules", "physics"):
        for key, value in (grouped[group] or {}).items():
            overrides[key] = value
    return defaults.effective_core(overrides) if overrides else {}


def get_effective_core():
    """Resolved core config (defaults merged with admin overrides)."""
    return defaults.effective_core(get_core_overrides())


def set_core_overrides(rules_overrides, physics_overrides):
    """Store validated rule/physics overrides (only values that differ from defaults)."""
    combined = {}
    for key, value in (rules_overrides or {}).items():
        combined[key] = value
    for key, value in (physics_overrides or {}).items():
        combined[key] = value
    resolved = defaults.effective_core(combined)

    def _differing(group):
        out = {}
        for key, spec in defaults.KNOBS.items():
            if spec["group"] != group:
                continue
            value = resolved.get(key, spec["value"])
            if value != spec["value"]:
                out[key] = value
        return out

    _set(CORE_RULES_KEY, _differing("rules"))
    _set(CORE_PHYSICS_KEY, _differing("physics"))


def reset_core():
    """Remove all core overrides (restore defaults), including the referee text."""
    for key in (CORE_RULES_KEY, CORE_PHYSICS_KEY, CORE_REFEREE_KEY):
        setting = AppSetting.query.filter_by(key=key).first()
        if setting:
            db.session.delete(setting)
    db.session.commit()


def get_referee_md():
    return _get(CORE_REFEREE_KEY, defaults.REFEREE_MD) or defaults.REFEREE_MD


def set_referee_md(text):
    _set(CORE_REFEREE_KEY, (text or "").strip() or defaults.REFEREE_MD)

