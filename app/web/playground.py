from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import agent_service, competition_service
from ..extensions import db
from ..models import AgentConfiguration, GameVersion, Playground, Team

bp = Blueprint("playground", __name__, url_prefix="/playground")


@bp.route("")
@login_required
def index():
    playgrounds = Playground.query.filter_by(owner_id=current_user.id).order_by(
        Playground.updated_at.desc()
    ).all()
    versions = GameVersion.query.order_by(GameVersion.id.desc()).all()
    return render_template("playground/index.html", playgrounds=playgrounds, versions=versions)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    version_id = request.form.get("game_version_id", type=int)
    name = request.form.get("name", "").strip() or "My Playground"
    version = GameVersion.query.get_or_404(version_id)
    blueprint = version.blueprint_json

    playground = Playground(
        owner_id=current_user.id,
        game_version_id=version.id,
        name=name,
        configuration_json={},
    )
    db.session.add(playground)
    db.session.flush()

    team_count = blueprint["competition"].get("teams", 2)
    for team_index in range(team_count):
        team = Team(
            playground_id=playground.id,
            name=f"Team {chr(ord('A') + team_index)}",
            configuration_json=agent_service.default_team_configuration(blueprint),
        )
        db.session.add(team)
        db.session.flush()

        role_counts = {}
        for role_id in agent_service.expand_agents(blueprint):
            role_counts[role_id] = role_counts.get(role_id, 0) + 1
            config = agent_service.default_agent_configuration(blueprint, role_id)
            config["name"] = role_id.title()
            db.session.add(
                AgentConfiguration(
                    team_id=team.id,
                    role=role_id,
                    configuration_json=config,
                )
            )

    db.session.commit()
    return redirect(url_for("playground.configure", playground_id=playground.id))


@bp.route("/<int:playground_id>", methods=["GET", "POST"])
@login_required
def configure(playground_id):
    playground = Playground.query.get_or_404(playground_id)
    blueprint = playground.game_version.blueprint_json

    if request.method == "POST":
        _save_configuration(playground)
        flash("Configuration saved.", "success")
        return redirect(url_for("playground.configure", playground_id=playground.id))

    return render_template("playground/configure.html", playground=playground, blueprint=blueprint)


def _save_configuration(playground):
    form = request.form
    for team in playground.teams:
        team_config = team.configuration_json or {}
        team_config["instructions"] = form.get(f"team_instructions_{team.id}", "")
        team_config["strategy"] = form.get(f"team_strategy_{team.id}", "")
        team.configuration_json = team_config

        for agent in team.agents:
            config = agent.configuration_json or {}
            config["instructions"] = form.get(f"agent_instructions_{agent.id}", "")
            config["model"] = form.get(f"agent_model_{agent.id}", "mock-model")
            config["temperature"] = request.form.get(f"agent_temperature_{agent.id}", type=float, default=0.2)
            config["max_tokens"] = request.form.get(f"agent_max_tokens_{agent.id}", type=int, default=256)
            config["selected_skills"] = request.form.getlist(f"agent_skills_{agent.id}")
            agent.configuration_json = config

    db.session.commit()


@bp.route("/<int:playground_id>/run", methods=["POST"])
@login_required
def run(playground_id):
    playground = Playground.query.get_or_404(playground_id)
    competition = competition_service.create_competition(playground, current_user)
    competition_service.enqueue_competition(competition)
    return redirect(url_for("competitions.view", competition_id=competition.id))
