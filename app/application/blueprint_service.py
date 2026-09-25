import os
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import Game, GameVersion
from .compiler_service import compile_files
from .importer_service import import_files
from .validation import validate_blueprint


def _templates_dir():
    return Path(current_app.config["GAME_TEMPLATES_DIR"])


def list_templates():
    templates_dir = _templates_dir()
    if not templates_dir.exists():
        return []
    return sorted(p.name for p in templates_dir.iterdir() if p.is_dir())


def _read_template(game_id):
    root = _templates_dir() / game_id
    files = {}
    for path in root.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(root))
            files[rel] = path.read_text(encoding="utf-8")
    return files


def load_template(game_id):
    files = _read_template(game_id)
    blueprint, errors = import_files(files)
    if errors:
        raise ValueError(f"Template {game_id} is invalid: {errors}")
    return blueprint


def create_game_from_template(owner_id, game_id):
    blueprint = load_template(game_id)
    return _create_game(owner_id, blueprint)


def _create_game(owner_id, blueprint):
    files = compile_files(blueprint)
    game = Game(
        owner_id=owner_id,
        name=blueprint["game"]["name"],
        description=blueprint["game"].get("description", ""),
        status="draft",
    )
    db.session.add(game)
    db.session.flush()

    version = GameVersion(
        game_id=game.id,
        version=blueprint["game"].get("version", "1.0.0"),
        blueprint_json=blueprint,
        blueprint_files=files,
    )
    db.session.add(version)
    db.session.flush()

    game.current_version_id = version.id
    db.session.commit()
    return game


def save_version(game, blueprint):
    """Validate, compile, and persist a new version of a game."""
    errors = validate_blueprint(blueprint)
    if errors:
        return None, errors

    files = compile_files(blueprint)
    version = GameVersion(
        game_id=game.id,
        version=blueprint["game"].get("version", "1.0.0"),
        blueprint_json=blueprint,
        blueprint_files=files,
    )
    db.session.add(version)
    db.session.flush()
    game.current_version_id = version.id
    db.session.commit()
    return version, []


def compile_blueprint(blueprint):
    return compile_files(blueprint)


def next_version_string(game):
    latest = (
        GameVersion.query.filter_by(game_id=game.id)
        .order_by(GameVersion.id.desc())
        .first()
    )
    if not latest:
        return "1.0.0"
    parts = latest.version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)
