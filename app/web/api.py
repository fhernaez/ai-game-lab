from flask import Blueprint, jsonify, request
from flask_login import login_required

from ..application import competition_service
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
    return jsonify(
        {
            "status": competition.status,
            "configuration": competition.configuration_json,
            "final_state": competition.final_state_json,
        }
    )
