from flask import Blueprint, render_template
from flask_login import login_required

from ..application import match_service
from ..models import Event, Match

bp = Blueprint("history", __name__, url_prefix="/history")


@bp.route("")
@login_required
def index():
    matches = match_service.history()
    return render_template("history/index.html", matches=matches)


@bp.route("/<int:match_id>")
@login_required
def detail(match_id):
    match = Match.query.get_or_404(match_id)
    events = (
        Event.query.filter_by(match_id=match.id)
        .order_by(Event.sequence_number.asc())
        .all()
    )
    return render_template("history/detail.html", match=match, events=events)
