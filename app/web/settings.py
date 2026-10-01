from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import settings_service
from ..domain.volleyball.body import parameters as body_parameters
from ..domain.volleyball.brain import skills as skills_mod, tools as tools_mod
from ..domain.volleyball.core import defaults, render as core_render
from ..infrastructure.llm import provider_ids

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("", methods=["GET", "POST"])
@login_required
def index():
    is_admin = current_user.role == "admin"
    providers = provider_ids()

    if request.method == "POST" and is_admin:
        provider_models = {}
        for pid in providers:
            raw = request.form.get(f"models_{pid}", "")
            provider_models[pid] = [m.strip() for m in raw.split(",") if m.strip()]
        settings_service.set_provider_models(provider_models)
        settings_service.set_default_model(request.form.get("default_model", ""))
        flash("Settings saved.", "success")
        return redirect(url_for("settings.index"))

    provider_models = settings_service.get_provider_models()
    default_model = settings_service.get_default_model()
    info = {
        "database_uri": _redact(current_app.config["SQLALCHEMY_DATABASE_URI"]),
        "default_provider": current_app.config["DEFAULT_PROVIDER"],
        "default_model": current_app.config["DEFAULT_MODEL"],
        "redis_url": "configured" if current_app.config.get("REDIS_URL") else "not configured",
    }
    return render_template(
        "settings/index.html",
        info=info,
        is_admin=is_admin,
        providers=providers,
        provider_models=provider_models,
        default_model=default_model,
    )


def _redact(uri):
    if "://" in uri and "@" in uri:
        scheme, rest = uri.split("://", 1)
        creds, host = rest.split("@", 1)
        return f"{scheme}://****@{host}"
    return uri


@bp.route("/core", methods=["GET", "POST"])
@login_required
def core():
    is_admin = current_user.role == "admin"

    if request.method == "POST":
        if not is_admin:
            flash("Administrator access required.", "error")
            return redirect(url_for("settings.core"))
        if request.form.get("restore"):
            settings_service.reset_core()
            flash("Core configuration reset to defaults.", "success")
        else:
            rules_ov, physics_ov = {}, {}
            for key, spec in defaults.KNOBS.items():
                raw = request.form.get(f"knob_{key}")
                if raw is None or raw == "":
                    continue
                target = rules_ov if spec["group"] == "rules" else physics_ov
                target[key] = raw
            settings_service.set_core_overrides(rules_ov, physics_ov)
            settings_service.set_referee_md(request.form.get("referee_md", ""))
            flash("Core configuration saved.", "success")
        return redirect(url_for("settings.core"))

    effective = settings_service.get_effective_core()
    referee_md = settings_service.get_referee_md()
    return render_template(
        "settings/core.html",
        knobs=defaults.KNOBS,
        effective=effective,
        referee_md=referee_md,
        rules_yaml=core_render.render_rules_yaml(effective),
        physics_yaml=core_render.render_physics_yaml(effective),
        is_admin=is_admin,
    )


def _float(raw, default):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _int(raw, default=1):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _strategy_from_form(prefix, form):
    """Read a strategy's fields from the form using the given field-name prefix."""
    attributes = {}
    for difficulty in ("easy", "medium", "hard"):
        attrs = {}
        for key in body_parameters.ATTRIBUTE_KEYS:
            raw = form.get(f"{prefix}_attrs_{difficulty}_{key}")
            attrs[key] = body_parameters.clamp_slider(_int(raw, 1)) if raw not in (None, "") else 1
        attributes[difficulty] = attrs
    return {
        "name": form.get(f"{prefix}_name", "").strip(),
        "description": form.get(f"{prefix}_description", "").strip(),
        "what": form.get(f"{prefix}_what", "").strip(),
        "effect": form.get(f"{prefix}_effect", "").strip(),
        "brain": {
            "persona": form.get(f"{prefix}_persona", "").strip(),
            "goal": form.get(f"{prefix}_goal", "").strip(),
            "skills": form.getlist(f"{prefix}_skills"),
            "tools": form.getlist(f"{prefix}_tools"),
            "params": {"temperature": _float(form.get(f"{prefix}_temperature"), 0.7)},
        },
        "attributes": attributes,
    }


@bp.route("/strategies", methods=["GET", "POST"])
@login_required
def strategies():
    is_admin = current_user.role == "admin"

    if request.method == "POST":
        if not is_admin:
            flash("Administrator access required.", "error")
            return redirect(url_for("settings.strategies"))
        if request.form.get("restore"):
            settings_service.reset_strategies()
            flash("Strategies reset to defaults.", "success")
            return redirect(url_for("settings.strategies"))
        delete_id = (request.form.get("delete_id") or "").strip()
        if delete_id:
            saved = settings_service.get_strategies()
            saved.pop(delete_id, None)
            settings_service.set_strategies(saved)
            flash(f"Deleted strategy {delete_id!r}.", "success")
            return redirect(url_for("settings.strategies"))

        data = {}
        for sid in request.form.getlist("sid"):
            sid = sid.strip()
            if sid:
                data[sid] = _strategy_from_form(sid, request.form)
        new_sid = (request.form.get("new_sid") or "").strip()
        if new_sid:
            data[new_sid] = _strategy_from_form("new", request.form)
        settings_service.set_strategies(data)
        flash("Strategies saved.", "success")
        return redirect(url_for("settings.strategies"))

    return render_template(
        "settings/strategies.html",
        strategies=settings_service.get_strategies(),
        skill_options=skills_mod.DEFAULT_SKILLS,
        tool_keys=tools_mod.TOOL_KEYS,
        attribute_keys=body_parameters.ATTRIBUTE_KEYS,
        attribute_labels=body_parameters.ATTRIBUTE_LABELS,
        budgets=body_parameters.DIFFICULTY_BUDGETS,
        is_admin=is_admin,
    )
