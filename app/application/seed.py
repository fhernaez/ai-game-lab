from flask import current_app

from ..extensions import db
from ..models import Game, User
from . import blueprint_service


def seed():
    _seed_admin()
    _seed_templates()


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


def _seed_templates():
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        return
    for game_id in blueprint_service.list_templates():
        blueprint = blueprint_service.load_template(game_id)
        existing = Game.query.filter_by(name=blueprint["game"]["name"]).first()
        if existing:
            continue
        blueprint_service.create_game_from_template(admin.id, game_id)
