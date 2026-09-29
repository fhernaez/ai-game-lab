from flask import current_app

from ..extensions import db
from ..models import User


def seed():
    _seed_admin()


def _seed_admin():
    username = current_app.config["ADMIN_USERNAME"]
    if User.query.filter_by(username=username).first():
        return
    admin = User(
        username=username,
        email=current_app.config["ADMIN_EMAIL"],
        role="admin",
    )
    admin.set_password(current_app.config["ADMIN_PASSWORD"])
    db.session.add(admin)
    db.session.commit()
