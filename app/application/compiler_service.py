"""Blueprint compiler: structured configuration -> file artifacts.

Deterministic: the same blueprint dict always produces the same files.
"""

import yaml

YAML_DUMP_KWARGS = {"sort_keys": True, "default_flow_style": False, "allow_unicode": True}

# Manifest carries the machine-readable game definition (no playground).
MANIFEST_KEYS = ["game", "competition", "teams", "referee", "resources", "engine"]


def _yaml(data):
    return yaml.safe_dump(data, **YAML_DUMP_KWARGS)


def compile_files(blueprint):
    """Return {filename: content} for every blueprint artifact."""
    files = {}

    manifest = {k: blueprint[k] for k in MANIFEST_KEYS if k in blueprint}
    files["manifest.yaml"] = _yaml(manifest)

    files["playground.yaml"] = _yaml({"playground": blueprint.get("playground", {})})

    markdown = blueprint.get("markdown", {})
    for name in ("game", "rules", "scoring", "referee"):
        files[f"{name}.md"] = markdown.get(name, "")

    for role, content in (markdown.get("agents") or {}).items():
        files[f"agents/{role}.md"] = content

    for skill, content in (markdown.get("skills") or {}).items():
        files[f"skills/{skill}.md"] = content

    return files
