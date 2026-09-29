from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import matchmaking_service, presence_service
from ..extensions import db
from ..models import Competition, GameVersion, User

bp = Blueprint("matchmaking", __name__)


@bp.route("/matchmaking")
@login_required
def index():
    mine = (
        Competition.query.filter(
            (Competition.host_id == current_user.id)
            | (Competition.guest_id == current_user.id)
        )
        .order_by(Competition.created_at.desc())
        .all()
    )
    versions = GameVersion.query.order_by(GameVersion.id.desc()).all()
    online = presence_service.online_users(exclude_id=current_user.id)
    return render_template(
        "matchmaking/index.html",
        competitions=mine,
        versions=versions,
        online=online,
    )


@bp.route("/matchmaking/create", methods=["POST"])
@login_required
def create():
    version = GameVersion.query.get_or_404(request.form.get("game_version_id", type=int))
    round_budget = request.form.get("round_budget", type=int)
    competition = matchmaking_service.create_competition(current_user, version, round_budget)
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/matchmaking/<int:competition_id>/invite", methods=["POST"])
@login_required
def invite(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    if competition.host_id != current_user.id:
        flash("Only the host can invite.", "error")
        return redirect(url_for("matchmaking.index"))
    username = request.form.get("username", "").strip()
    guest = User.query.filter_by(username=username).first()
    if guest is None:
        flash("No such user.", "error")
        return redirect(url_for("competitions.view", competition_id=competition.id))
    if guest.id == current_user.id:
        flash("You cannot invite yourself.", "error")
        return redirect(url_for("competitions.view", competition_id=competition.id))
    matchmaking_service.invite(competition, guest)
    flash(f"Invited {guest.username}.", "success")
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/matchmaking/<int:competition_id>/accept", methods=["POST"])
@login_required
def accept(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    matchmaking_service.accept(competition, current_user)
    return redirect(url_for("competitions.view", competition_id=competition.id))


@bp.route("/matchmaking/<int:competition_id>/decline", methods=["POST"])
@login_required
def decline(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    matchmaking_service.decline(competition, current_user)
    return redirect(url_for("matchmaking.index"))
