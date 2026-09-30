from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import settings_service
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
