from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import settings_service, team_service
from ..domain.volleyball import attributes
from ..extensions import db
from ..infrastructure.llm import provider_ids
from ..models import Match, Team

bp = Blueprint("teams", __name__, url_prefix="/matches")


def _my_team(match):
    return Team.query.filter_by(match_id=match.id, player_id=current_user.id).first()


@bp.route("/<int:match_id>/team", methods=["GET", "POST"])
@login_required
def configure(match_id):
    match = Match.query.get_or_404(match_id)
    team = _my_team(match)
    if team is None:
        flash("You are not part of this match.", "error")
        return redirect(url_for("matches.view", match_id=match.id))

    if request.method == "POST":
        _save_team(team, match)
        if team_service.budget_ok(team, match.difficulty):
            flash("Team saved.", "success")
            return redirect(url_for("teams.configure", match_id=match.id))
        flash(
            f"Over budget: difficulty {match.difficulty} allows "
            f"{attributes.difficulty_budget(match.difficulty)} points; "
            f"your team costs {team_service.team_cost(team)}.",
            "error",
        )
        return redirect(url_for("teams.configure", match_id=match.id))

    provider_models = settings_service.get_provider_models()
    return render_template(
        "teams/configure.html",
        match=match,
        team=team,
        attribute_keys=attributes.ATTRIBUTE_KEYS,
        attribute_labels=attributes.ATTRIBUTE_LABELS,
        attribute_descriptions=attributes.ATTRIBUTE_DESCRIPTIONS,
        archetypes=attributes.ARCHETYPES,
        providers=provider_ids(),
        provider_models=provider_models,
        budget=attributes.difficulty_budget(match.difficulty),
        cost=team_service.team_cost(team),
    )


def _int(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _save_team(team, match):
    form = request.form
    cfg = dict(team.configuration_json or {})
    cfg["strategy"] = form.get("strategy", "")

    archetype = form.get("archetype", "")
    for p in team.players:
        pcfg = dict(p.configuration_json or {})
        attrs = {}
        for key in attributes.ATTRIBUTE_KEYS:
            attrs[key] = attributes.clamp_slider(
                _int(form.get(f"attr_{p.id}_{key}"), pcfg.get("attributes", {}).get(key, 1))
            )
        pcfg["attributes"] = attrs
        if archetype and archetype in attributes.ARCHETYPES:
            pcfg = team_service.apply_archetype(pcfg, archetype)
        pcfg["model"] = form.get(f"model_{p.id}", "")
        pcfg["temperature"] = _float(form.get(f"temperature_{p.id}"), 0.7)
        pcfg["max_tokens"] = _int(form.get(f"max_tokens_{p.id}"), 256)
        pcfg["top_p"] = _float(form.get(f"top_p_{p.id}"), 1.0)
        pcfg["frequency_penalty"] = _float(form.get(f"frequency_penalty_{p.id}"), 0.0)
        pcfg["presence_penalty"] = _float(form.get(f"presence_penalty_{p.id}"), 0.0)
        pcfg["stop"] = [s for s in form.get(f"stop_{p.id}", "").split(",") if s]
        pcfg["response_format"] = form.get(f"response_format_{p.id}", "json")
        pcfg["instructions"] = form.get(f"instructions_{p.id}", "")
        p.configuration_json = pcfg

    cfg["archetype"] = archetype or None
    team.configuration_json = cfg
    db.session.commit()
