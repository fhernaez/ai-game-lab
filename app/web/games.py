from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import blueprint_service, importer_service
from ..extensions import db
from ..models import Game, GameVersion

bp = Blueprint("games", __name__)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _current_blueprint(game):
    version = GameVersion.query.get(game.current_version_id)
    return version.blueprint_json if version else None


@bp.route("/games")
@login_required
def index():
    games = Game.query.order_by(Game.updated_at.desc()).all()
    templates = blueprint_service.list_templates()
    return render_template("games/index.html", games=games, templates=templates)


@bp.route("/games/create/<template_id>", methods=["POST"])
@login_required
def create_from_template(template_id):
    try:
        blueprint_service.create_game_from_template(current_user.id, template_id)
        flash("Game created from template.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("games.index"))


@bp.route("/games/<int:game_id>")
@login_required
def detail(game_id):
    game = Game.query.get_or_404(game_id)
    versions = GameVersion.query.filter_by(game_id=game.id).order_by(GameVersion.id.desc()).all()
    return render_template("games/detail.html", game=game, versions=versions)


@bp.route("/games/<int:game_id>/design", methods=["GET", "POST"])
@login_required
def design(game_id):
    game = Game.query.get_or_404(game_id)
    blueprint = _current_blueprint(game)

    if request.method == "POST":
        blueprint = _blueprint_from_form(blueprint)
        version, errors = blueprint_service.save_version(game, blueprint)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            flash(f"Saved version {version.version}.", "success")
            return redirect(url_for("games.detail", game_id=game.id))

    return render_template("games/design.html", game=game, blueprint=blueprint)


def _blueprint_from_form(current):
    form = request.form
    roles = current.get("teams", {}).get("roles", [])
    agents_md = dict(current.get("markdown", {}).get("agents", {}))
    skills_md = dict(current.get("markdown", {}).get("skills", {}))

    new_roles = []
    for idx, role in enumerate(roles):
        new_roles.append(
            {
                "id": role["id"],
                "count": _int(form.get(f"role_count_{idx}"), role.get("count", 1)),
                "required": form.get(f"role_required_{idx}") == "on",
            }
        )

    def _comma(key):
        return [s.strip() for s in form.get(key, "").split(",") if s.strip()]

    blueprint = {
        "game": {
            "id": current["game"]["id"],
            "name": form.get("name", current["game"].get("name", "")),
            "version": form.get("version", current["game"].get("version", "1.0.0")),
            "description": form.get("description", current["game"].get("description", "")),
        },
        "competition": {
            "min_players": _int(form.get("min_players"), 2),
            "max_players": _int(form.get("max_players"), 2),
            "teams": _int(form.get("competition_teams"), 2),
            "turn_mode": form.get("turn_mode", "sequential"),
            "action_timeout_seconds": _int(form.get("action_timeout_seconds"), 30),
            "duration": {
                "type": form.get("duration_type", "turns"),
                "value": _int(form.get("duration_value"), 20),
            },
        },
        "teams": {
            "agents_per_team": _int(form.get("agents_per_team"), 3),
            "roles": new_roles,
        },
        "referee": {
            "enabled": form.get("referee_enabled") == "on",
            "agent_template": current.get("referee", {}).get("agent_template", "referee"),
        },
        "resources": {
            "team_token_budget": _int(form.get("team_token_budget"), 50000),
            "team_memory_budget": _int(form.get("team_memory_budget"), 12000),
            "max_concurrent_agents": _int(form.get("max_concurrent_agents"), 3),
        },
        "engine": current.get("engine", {}),
        "playground": {
            "editable": _comma("playground_editable") or current.get("playground", {}).get("editable", []),
            "locked": _comma("playground_locked") or current.get("playground", {}).get("locked", []),
        },
        "markdown": {
            "game": form.get("markdown_game", ""),
            "rules": form.get("markdown_rules", ""),
            "scoring": form.get("markdown_scoring", ""),
            "referee": form.get("markdown_referee", ""),
            "agents": {role["id"]: form.get(f"markdown_agent_{role['id']}", agents_md.get(role["id"], "")) for role in roles},
            "skills": {skill: form.get(f"markdown_skill_{skill}", content) for skill, content in skills_md.items()},
        },
    }
    return blueprint


@bp.route("/games/<int:game_id>/technical", methods=["GET", "POST"])
@login_required
def technical(game_id):
    game = Game.query.get_or_404(game_id)
    blueprint = _current_blueprint(game)

    if request.method == "POST":
        files = {}
        for name in request.form.getlist("filename"):
            files[name] = request.form.get(f"content_{name}", "")
        new_blueprint, errors = importer_service.import_files(files)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            new_blueprint["game"]["version"] = blueprint_service.next_version_string(game)
            version, errors = blueprint_service.save_version(game, new_blueprint)
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                flash(f"Technical edits saved as version {version.version}.", "success")
                return redirect(url_for("games.technical", game_id=game.id))

    files = blueprint_service.compile_blueprint(blueprint)
    file_rows = {name: max(content.count("\n") + 1, 6) for name, content in files.items()}
    return render_template(
        "games/technical.html",
        game=game,
        blueprint=blueprint,
        files=files,
        file_rows=file_rows,
    )
