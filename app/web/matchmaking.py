from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import matchmaking_service, presence_service
from ..models import Match, User

bp = Blueprint("matchmaking", __name__)


@bp.route("/matchmaking")
@login_required
def index():
    mine = (
        Match.query.filter(
            (Match.host_id == current_user.id) | (Match.guest_id == current_user.id)
        )
        .order_by(Match.created_at.desc())
        .all()
    )
    online = presence_service.online_users(exclude_id=current_user.id)
    return render_template("matchmaking/index.html", matches=mine, online=online)


@bp.route("/matchmaking/create", methods=["POST"])
@login_required
def create():
    difficulty = request.form.get("difficulty", "medium")
    match = matchmaking_service.create_match(current_user, difficulty)
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/matchmaking/<int:match_id>/invite", methods=["POST"])
@login_required
def invite(match_id):
    match = Match.query.get_or_404(match_id)
    if match.host_id != current_user.id:
        flash("Only the host can invite.", "error")
        return redirect(url_for("matchmaking.index"))
    guest = User.query.filter_by(username=request.form.get("username", "").strip()).first()
    if guest is None or guest.id == current_user.id:
        flash("Invalid player.", "error")
        return redirect(url_for("matches.view", match_id=match.id))
    matchmaking_service.invite(match, guest)
    flash(f"Invited {guest.username}.", "success")
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/matchmaking/<int:match_id>/accept", methods=["POST"])
@login_required
def accept(match_id):
    match = Match.query.get_or_404(match_id)
    matchmaking_service.accept(match, current_user)
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/matchmaking/<int:match_id>/decline", methods=["POST"])
@login_required
def decline(match_id):
    match = Match.query.get_or_404(match_id)
    matchmaking_service.decline(match, current_user)
    return redirect(url_for("matchmaking.index"))
