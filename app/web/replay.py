from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Action, Competition, Event, ResourceUsage

bp = Blueprint("replay", __name__, url_prefix="/competitions")


@bp.route("/<int:competition_id>/replay")
@login_required
def view(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    events = (
        Event.query.filter_by(competition_id=competition.id)
        .order_by(Event.sequence_number.asc())
        .all()
    )
    actions = (
        Action.query.filter_by(competition_id=competition.id)
        .order_by(Action.id.asc())
        .all()
    )
    usage = (
        ResourceUsage.query.filter_by(competition_id=competition.id)
        .order_by(ResourceUsage.id.asc())
        .all()
    )
    return render_template(
        "replay/view.html",
        competition=competition,
        events=events,
        actions=actions,
        usage=usage,
    )
