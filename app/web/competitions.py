from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Competition

bp = Blueprint("competitions", __name__, url_prefix="/competitions")


@bp.route("")
@login_required
def index():
    competitions = Competition.query.order_by(Competition.created_at.desc()).all()
    return render_template("competitions/index.html", competitions=competitions)


@bp.route("/<int:competition_id>")
@login_required
def view(competition_id):
    competition = Competition.query.get_or_404(competition_id)
    return render_template("competitions/view.html", competition=competition)
