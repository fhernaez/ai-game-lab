"""Render the core configuration as a file view (rules.yaml, physics.yaml, referee.md)."""

import yaml

from . import defaults


def _group(core, group):
    return {
        key: core[key]
        for key in defaults.KNOBS
        if defaults.KNOBS[key]["group"] == group and key in core
    }


def render_rules_yaml(core=None):
    core = core or defaults.DEFAULTS
    rules = _group(core, "rules")
    rules["net_y"] = defaults.net_y(core)
    return yaml.safe_dump(rules, sort_keys=False, default_flow_style=False).strip()


def render_physics_yaml(core=None):
    core = core or defaults.DEFAULTS
    return yaml.safe_dump(_group(core, "physics"), sort_keys=False, default_flow_style=False).strip()


def render_referee_md(text=None):
    return (text or defaults.REFEREE_MD).strip()
