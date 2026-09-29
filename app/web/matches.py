from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..application import match_service, matchmaking_service, presence_service
from ..models import Match, Team

bp = Blueprint("matches", __name__, url_prefix="/matches")


def _my_team(match):
    return Team.query.filter_by(match_id=match.id, player_id=current_user.id).first()


@bp.route("/<int:match_id>")
@login_required
def view(match_id):
    match = Match.query.get_or_404(match_id)
    my_team = _my_team(match)
    online = presence_service.online_users(exclude_id=current_user.id)
    return render_template(
        "matches/view.html",
        match=match,
        my_team=my_team,
        online=online,
        is_host=match.host_id == current_user.id,
        is_guest=match.guest_id == current_user.id,
    )


@bp.route("/<int:match_id>/ready", methods=["POST"])
@login_required
def ready(match_id):
    match = Match.query.get_or_404(match_id)
    matchmaking_service.mark_ready(match, current_user)
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/<int:match_id>/cancel", methods=["POST"])
@login_required
def cancel(match_id):
    match = Match.query.get_or_404(match_id)
    matchmaking_service.cancel(match, current_user)
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/<int:match_id>/stop", methods=["POST"])
@login_required
def stop(match_id):
    match = Match.query.get_or_404(match_id)
    match_service.stop_match(match)
    return redirect(url_for("matches.view", match_id=match.id))


@bp.route("/<int:match_id>/delete", methods=["POST"])
@login_required
def delete(match_id):
    match = Match.query.get_or_404(match_id)
    if current_user.id not in (match.host_id, match.guest_id):
        flash("You cannot delete this match.", "error")
        return redirect(url_for("matches.view", match_id=match.id))
    match_service.delete_match(match)
    flash("Match deleted.", "success")
    return redirect(url_for("matchmaking.index"))
