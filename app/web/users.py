from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Match, Team, User

bp = Blueprint("users", __name__, url_prefix="/users")

ROLES = ["admin", "teacher", "student"]


def _admin_only():
    if current_user.role != "admin":
        flash("Administrator access required.", "error")
        return False
    return True


@bp.route("")
@login_required
def index():
    if not _admin_only():
        return redirect(url_for("matchmaking.index"))
    users = User.query.order_by(User.username).all()
    return render_template("users/index.html", users=users, roles=ROLES)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    if not _admin_only():
        return redirect(url_for("users.index"))
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "student")
    password = request.form.get("password", "")
    if not username or not email or not password:
        flash("Username, email, and password are required.", "error")
        return redirect(url_for("users.index"))
    if role not in ROLES:
        role = "student"
    if User.query.filter_by(username=username).first():
        flash("Username already taken.", "error")
        return redirect(url_for("users.index"))
    if User.query.filter_by(email=email).first():
        flash("Email already in use.", "error")
        return redirect(url_for("users.index"))
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Username or email already in use.", "error")
        return redirect(url_for("users.index"))
    flash(f"Created {role} user {username!r}.", "success")
    return redirect(url_for("users.index"))


@bp.route("/<int:user_id>/role", methods=["POST"])
@login_required
def change_role(user_id):
    if not _admin_only():
        return redirect(url_for("users.index"))
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("users.index"))
    role = request.form.get("role", user.role)
    if role in ROLES:
        user.role = role
        db.session.commit()
        flash(f"Updated {user.username} to {role}.", "success")
    return redirect(url_for("users.index"))


@bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
def delete(user_id):
    if not _admin_only():
        return redirect(url_for("users.index"))
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "error")
        return redirect(url_for("users.index"))
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("users.index"))

    has_data = (
        Match.query.filter(
            (Match.host_id == user.id) | (Match.guest_id == user.id)
        ).first()
        or Team.query.filter_by(player_id=user.id).first()
    )
    if has_data:
        flash(
            f"Cannot delete {user.username}: they own teams or matches.",
            "error",
        )
        return redirect(url_for("users.index"))

    db.session.delete(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f"Cannot delete {user.username}: referenced by other data.", "error")
        return redirect(url_for("users.index"))
    flash(f"Deleted user {user.username}.", "success")
    return redirect(url_for("users.index"))
