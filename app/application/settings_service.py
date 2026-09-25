"""Admin settings: role-level default provider/model, stored in the DB."""

from flask import current_app

from ..extensions import db
from ..models import AppSetting, GameVersion

ROLE_DEFAULTS_KEY = "role_defaults"
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


def get_role_defaults():
    return _get(ROLE_DEFAULTS_KEY, {}) or {}


def set_role_defaults(mapping):
    _set(ROLE_DEFAULTS_KEY, dict(mapping))


def get_default_model():
    return _get(DEFAULT_MODEL_KEY, "") or ""


def set_default_model(ref):
    _set(DEFAULT_MODEL_KEY, ref or "")


def available_roles():
    """Union of role ids across all game versions (for the admin editor)."""
    roles = set()
    for version in GameVersion.query.all():
        blueprint = version.blueprint_json or {}
        for role in blueprint.get("teams", {}).get("roles", []):
            if role.get("id"):
                roles.add(role["id"])
    return sorted(roles)


def resolve_agent_model(role, explicit_model):
    """Return the effective model reference ("provider:model") for an agent.

    Precedence: explicit agent model -> role default -> global default -> None
    (the caller then falls back to the registry's global default).
    """
    if explicit_model:
        return explicit_model
    role_defaults = get_role_defaults()
    if role in role_defaults and role_defaults[role]:
        return role_defaults[role]
    return get_default_model() or None
