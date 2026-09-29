from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import competition_service, matchmaking_service, presence_service, settings_service
from ..extensions import db
from ..infrastructure.llm import provider_ids
from ..models import Competition, Crew

bp = Blueprint("competitions", __name__, url_prefix="/competitions")


def _my_crew(competition):
    return Crew.query.filter_by(
        competition_id=competition.id, player_id=current_user.id
    ).first()


@bp.route("")
@login_required
def index():
    competitions = (
        Competition.query.filter(
            (Competition.host_id == current_user.id)
            | (Competition.guest_id == current_user.id)
        )
        .order_by(Competition.created_at.desc())
        .all()
    )
    return render_template("competitions/index.html", competitions=competitions)


@bp.route("/<int:competition_id>")
@login_required
def view(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    my_crew = _my_crew(competition)
    online = presence_service.online_users(exclude_id=current_user.id)
    return render_template(
        "competitions/view.html",
        competition=competition,
        my_crew=my_crew,
        online=online,
        is_host=competition.host_id == current_user.id,
        is_guest=competition.guest_id == current_user.id,
    )


@bp.route("/<int:competition_id>/crew", methods=["GET", "POST"])
@login_required
def crew(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    my_crew = _my_crew(competition)
    if my_crew is None:
        flash("You are not part of this competition.", "error")
        return redirect(url_for("competitions.view", competition_id=competition.id))

    if request.method == "POST":
        _save_crew(my_crew)
        flash("Crew saved.", "success")
        return redirect(url_for("competitions.crew", competition_id=competition.id))

    provider_models = settings_service.get_provider_models()
    return render_template(
        "competitions/crew.html",
        competition=competition,
        crew=my_crew,
        providers=provider_ids(),
        provider_models=provider_models,
    )


def _save_crew(crew):
    form = request.form
    cfg = dict(crew.configuration_json or {})
    cfg["instructions"] = form.get("crew_instructions", "")
    cfg["strategy"] = form.get("crew_strategy", "")
    crew.configuration_json = cfg

    for member in crew.members:
        mcfg = dict(member.configuration_json or {})
        mcfg["instructions"] = form.get(f"instructions_{member.id}", "")
        mcfg["model"] = form.get(f"model_{member.id}", "")
        mcfg["temperature"] = _float(form.get(f"temperature_{member.id}"), 0.7)
        mcfg["max_tokens"] = _int(form.get(f"max_tokens_{member.id}"), 512)
        mcfg["top_p"] = _float(form.get(f"top_p_{member.id}"), 1.0)
        mcfg["frequency_penalty"] = _float(form.get(f"frequency_penalty_{member.id}"), 0.0)
        mcfg["presence_penalty"] = _float(form.get(f"presence_penalty_{member.id}"), 0.0)
        mcfg["stop"] = [s for s in form.get(f"stop_{member.id}", "").split(",") if s]
        mcfg["response_format"] = form.get(f"response_format_{member.id}", "json")
        member.configuration_json = mcfg
    db.session.commit()


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@bp.route("/<int:competition_id>/ready", methods=["POST"])
@login_required
def ready(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    matchmaking_service.mark_ready(competition, current_user)
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/<int:competition_id>/cancel", methods=["POST"])
@login_required
def cancel(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    matchmaking_service.cancel(competition, current_user)
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/<int:competition_id>/stop", methods=["POST"])
@login_required
def stop(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    competition_service.stop_competition(competition)
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/<int:competition_id>/delete", methods=["POST"])
@login_required
def delete(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    if current_user.id not in (competition.host_id, competition.guest_id):
        flash("You cannot delete this competition.", "error")
        return redirect(url_for("competitions.view", competition_id=competition.id))
    competition_service.delete_competition(competition)
    flash("Competition deleted.", "success")
    return redirect(url_for("competitions.index"))
