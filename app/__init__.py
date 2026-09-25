import os
from pathlib import Path

import click
from flask import Flask

from config import Config

from .extensions import db, login_manager, migrate


def create_app(config_object=None):
    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )
    app.config.from_object(config_object or Config)

    # Ensure instance dir exists for SQLite.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."

    from .models import User  # noqa: F401

    register_blueprints(app)
    register_cli(app)

    return app


def register_blueprints(app):
    from .web.auth import bp as auth_bp
    from .web.settings import bp as settings_bp
    from .web.games import bp as games_bp
    from .web.playground import bp as playground_bp
    from .web.competitions import bp as competitions_bp
    from .web.replay import bp as replay_bp
    from .web.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(playground_bp)
    app.register_blueprint(competitions_bp)
    app.register_blueprint(replay_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        from flask import redirect, url_for

        return redirect(url_for("games.index"))


def register_cli(app):
    @app.cli.command("seed")
    def seed_command():
        """Create the admin user and load the seed game templates.

        Run `flask db upgrade` first to create the database schema.
        """
        from .application.seed import seed

        seed()
        print("Seed complete.")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("email")
    @click.argument("role", type=click.Choice(["admin", "teacher", "student"]))
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Password for the new user (prompted if omitted).",
    )
    def create_user_command(username, email, role, password):
        """Create a user with the given role."""
        from .models import User

        if User.query.filter_by(username=username).first():
            raise click.ClickException(f"User {username!r} already exists.")
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {role} user {username!r}.")

    @app.cli.command("worker")
    @click.option("--queue", default="competitions", help="Queue name to listen on.")
    def worker_command(queue):
        """Start a background worker that processes queued competition runs."""
        from redis import Redis
        from rq import Connection, Queue, Worker

        redis_url = app.config.get("REDIS_URL") or app.config.get("RQ_REDIS_URL")
        if not redis_url:
            raise click.ClickException(
                "REDIS_URL is not configured; cannot start a worker."
            )
        connection = Redis.from_url(redis_url)
        with Connection(connection):
            worker = Worker([Queue(queue, connection=connection)])
            click.echo(f"Worker listening on queue {queue!r}.")
            worker.work()
