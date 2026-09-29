from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import settings_service
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
