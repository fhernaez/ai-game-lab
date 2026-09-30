from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..application import match_service, presence_service
from ..models import Match

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/matches/<int:match_id>/events")
@login_required
def events(match_id):
    match = Match.query.get_or_404(match_id)
    after = request.args.get("after", type=int)
    result = match_service.events_after(match, after)
    return jsonify({"events": result, "status": match.status})


@bp.route("/matches/<int:match_id>/state")
@login_required
def state(match_id):
    match = Match.query.get_or_404(match_id)
    teams = []
    for team in match.teams:
        teams.append(
            {
                "name": team.name,
                "player": team.player.username if team.player else "",
                "players": [
                    {
                        "slot": p.slot,
                        "name": (p.configuration_json or {}).get("name", f"Player {p.slot}"),
                        "parameters": ((p.configuration_json or {}).get("body") or {}).get("parameters", {}),
                    }
                    for p in sorted(team.players, key=lambda x: x.slot)
                ],
            }
        )
    return jsonify(
        {
            "status": match.status,
            "difficulty": match.difficulty,
            "host_ready": match.host_ready,
            "guest_ready": match.guest_ready,
            "final_state": match.final_state_json,
            "core_config": match.core_config_json,
            "teams": teams,
        }
    )


@bp.route("/online-users")
@login_required
def online_users():
    users = presence_service.online_users(exclude_id=current_user.id)
    return jsonify({"users": [{"id": u.id, "username": u.username} for u in users]})
