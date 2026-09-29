"""Blueprint importer: file artifacts -> structured configuration.

YAML/JSON are parsed and validated before being reconciled. Markdown files
are stored verbatim as authored natural-language text.
"""

import json

import yaml

from .validation import validate_blueprint

YAML_KEYS = ["game", "competition", "teams", "referee", "resources", "engine", "playground"]


def _parse_yaml(text):
    return yaml.safe_load(text) or {}


def parse_files(files):
    """Reconstruct a blueprint dict from a mapping of {filename: content}."""
    blueprint = {}

    manifest = _parse_yaml(files.get("manifest.yaml", ""))
    for key in YAML_KEYS:
        if key in manifest:
            blueprint[key] = manifest[key]

    playground = _parse_yaml(files.get("playground.yaml", ""))
    if isinstance(playground, dict) and "playground" in playground:
        blueprint["playground"] = playground["playground"]

    markdown = {
        "game": files.get("game.md", ""),
        "rules": files.get("rules.md", ""),
        "scoring": files.get("scoring.md", ""),
        "referee": files.get("referee.md", ""),
        "agents": {},
        "skills": {},
    }

    for filename, content in files.items():
        if filename.startswith("agents/") and filename.endswith(".md"):
            markdown["agents"][filename[len("agents/"): -3]] = content
        elif filename.startswith("skills/") and filename.endswith(".md"):
            markdown["skills"][filename[len("skills/"): -3]] = content

    blueprint["markdown"] = markdown
    return blueprint


def parse_json(text):
    return json.loads(text)


def import_files(files):
    """Parse and validate files, returning (blueprint, errors)."""
    try:
        blueprint = parse_files(files)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    errors = validate_blueprint(blueprint)
    return blueprint, errors


def dump_json(blueprint):
    return json.dumps(blueprint, indent=2, sort_keys=True)
