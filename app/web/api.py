from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..application import competition_service, presence_service
from ..models import Competition

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/competitions/<int:competition_id>/events")
@login_required
def events(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    after = request.args.get("after", type=int)
    result = competition_service.events_after(competition, after)
    return jsonify({"events": result, "status": competition.status})


@bp.route("/competitions/<int:competition_id>/state")
@login_required
def state(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    crews = [
        {
            "name": c.name,
            "player": c.player.username if c.player else "",
            "members": [
                {"role": m.role, "speak_order": m.speak_order, "is_speaker": m.is_speaker}
                for m in sorted(c.members, key=lambda x: x.speak_order)
            ],
        }
        for c in competition.crews
    ]
    return jsonify(
        {
            "status": competition.status,
            "round_budget": competition.round_budget,
            "final_state": competition.final_state_json,
            "crews": crews,
        }
    )


@bp.route("/online-users")
@login_required
def online_users():
    users = presence_service.online_users(exclude_id=current_user.id)
    return jsonify({"users": [{"id": u.id, "username": u.username} for u in users]})
