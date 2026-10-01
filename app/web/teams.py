from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import settings_service, team_service
from ..domain.volleyball.body import actuators, parameters as body_parameters
from ..domain.volleyball.brain import render as brain_render
from ..domain.volleyball.brain import sensors, skills, strategies as strategies_mod, tools
from ..domain.volleyball.core import render as core_render
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
            f"{body_parameters.difficulty_budget(match.difficulty)} points; "
            f"your team costs {team_service.team_cost(team)}.",
            "error",
        )
        return redirect(url_for("teams.configure", match_id=match.id))

    provider_models = settings_service.get_provider_models()
    return render_template(
        "teams/configure.html",
        match=match,
        team=team,
        attribute_keys=body_parameters.ATTRIBUTE_KEYS,
        attribute_labels=body_parameters.ATTRIBUTE_LABELS,
        attribute_descriptions=body_parameters.ATTRIBUTE_DESCRIPTIONS,
        attribute_effects=body_parameters.ATTRIBUTE_EFFECTS,
        archetypes=body_parameters.ARCHETYPES,
        strategies=settings_service.get_strategies(),
        actuator_keys=actuators.ACTUATOR_KEYS,
        actuators=actuators.ACTUATORS,
        sensors=sensors.SENSORS,
        sensor_labels=sensors.SENSOR_LABELS,
        tool_keys=tools.TOOL_KEYS,
        tools=tools.TOOLS,
        default_skills=skills.DEFAULT_SKILLS,
        providers=provider_ids(),
        provider_models=provider_models,
        budget=body_parameters.difficulty_budget(match.difficulty),
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
    cfg["strategy_preset"] = form.get("strategy_preset", "") or None
    selected_strategy = settings_service.get_strategies().get(form.get("strategy_preset", ""))

    archetype = form.get("archetype", "")
    for p in team.players:
        pcfg = dict(p.configuration_json or {})
        brain = dict(pcfg.get("brain") or {})
        body = dict(pcfg.get("body") or {})

        attrs = {}
        for key in body_parameters.ATTRIBUTE_KEYS:
            attrs[key] = body_parameters.clamp_slider(
                _int(form.get(f"attr_{p.id}_{key}"), body.get("parameters", {}).get(key, 1))
            )
        if selected_strategy:
            strat_attrs = strategies_mod.strategy_attributes(selected_strategy, match.difficulty)
            if strat_attrs:
                attrs = dict(strat_attrs)
        elif archetype and archetype in body_parameters.ARCHETYPES:
            attrs = body_parameters.archetype_attributes(archetype)
        body["parameters"] = attrs
        body["actuators"] = form.getlist(f"actuators_{p.id}") or list(actuators.ACTUATOR_KEYS)

        brain["persona"] = form.get(f"persona_{p.id}", brain.get("persona", ""))
        brain["goal"] = form.get(f"goal_{p.id}", brain.get("goal", "Win the point."))
        brain["task"] = form.get(f"task_{p.id}", brain.get("task", ""))
        brain["model"] = form.get(f"model_{p.id}", brain.get("model", ""))
        brain["tools"] = form.getlist(f"tools_{p.id}") or list(tools.TOOL_KEYS)
        brain["sensors"] = form.getlist(f"sensors_{p.id}") or list(sensors.SENSORS)
        brain["skills"] = skills.skills_by_ids(form.getlist(f"skills_{p.id}")) or skills.load_default_skills()

        params = dict(brain.get("params") or team_service.default_brain_params())
        params["temperature"] = _float(form.get(f"temperature_{p.id}"), params.get("temperature", 0.7))
        params["max_tokens"] = _int(form.get(f"max_tokens_{p.id}"), params.get("max_tokens", 256))
        params["top_p"] = _float(form.get(f"top_p_{p.id}"), params.get("top_p", 1.0))
        params["frequency_penalty"] = _float(
            form.get(f"frequency_penalty_{p.id}"), params.get("frequency_penalty", 0.0)
        )
        params["presence_penalty"] = _float(
            form.get(f"presence_penalty_{p.id}"), params.get("presence_penalty", 0.0)
        )
        brain["params"] = params

        # A chosen strategy overrides persona/goal/skills/tools/params for both players.
        if selected_strategy:
            brain = strategies_mod.apply_strategy(brain, selected_strategy)

        pcfg["brain"] = brain
        pcfg["body"] = body
        p.configuration_json = pcfg

    cfg["archetype"] = archetype or None
    team.configuration_json = cfg
    db.session.commit()


@bp.route("/<int:match_id>/advanced")
@login_required
def advanced(match_id):
    match = Match.query.get_or_404(match_id)
    team = _my_team(match)
    if team is None:
        flash("You are not part of this match.", "error")
        return redirect(url_for("matches.view", match_id=match.id))

    agent_files = []
    for p in sorted(team.players, key=lambda x: x.slot):
        cfg = p.configuration_json or {}
        brain = cfg.get("brain") or {}
        body = cfg.get("body") or {}
        agent_files.append(
            {
                "slot": p.slot,
                "name": cfg.get("name", f"Player {p.slot}"),
                "agent_md": brain_render.render_agent_md(brain),
                "skills_md": brain_render.render_skills_md(brain.get("skills")),
                "tools_yaml": brain_render.render_tools_yaml(brain.get("tools")),
                "body_yaml": brain_render.render_body_yaml(body),
            }
        )

    effective = settings_service.get_effective_core()
    core_files = {
        "rules_yaml": core_render.render_rules_yaml(effective),
        "physics_yaml": core_render.render_physics_yaml(effective),
        "referee_md": core_render.render_referee_md(settings_service.get_referee_md()),
    }

    return render_template(
        "teams/advanced.html", match=match, team=team, agent_files=agent_files, core_files=core_files
    )
