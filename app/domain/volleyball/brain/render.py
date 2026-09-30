"""Render a player's brain/body config as the agent file view.

These functions only *serialize* the structured config into Markdown/YAML text for
the read-only "files" view (agent.md, skills/*.md, tools.yaml, body.yaml). Editing
happens through the structured form in ``teams/configure.html``.
"""

import yaml

from . import skills as skills_mod, tools as tools_mod
from ..body import actuators as actuators_mod, parameters as parameters_mod


def render_agent_md(brain):
    brain = brain or {}
    params = brain.get("params") or {}
    lines = [
        "# Agent",
        "",
        "## Persona",
        (brain.get("persona") or "").strip() or "(none)",
        "",
        "## Goal",
        (brain.get("goal") or "").strip() or "(none)",
        "",
        "## Task",
        (brain.get("task") or "").strip() or "(set by the engine each play)",
        "",
        "## Model",
        brain.get("model") or "(default model)",
        "",
        "## Model parameters",
    ]
    for key in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"):
        lines.append(f"- {key}: {params.get(key)}")
    return "\n".join(lines).strip()


def render_skills_md(skills):
    skills = skills or []
    if not skills:
        return "# Skills\n\n(none)"
    out = ["# Skills", ""]
    for s in skills:
        out.append(f"## {s.get('title', s.get('id', 'skill'))}")
        out.append("")
        out.append(f"**What it is:** {s.get('what', '')}")
        out.append("")
        out.append(f"**Effect:** {s.get('effect', '')}")
        out.append("")
    return "\n".join(out).strip()


def render_tools_yaml(tool_ids):
    tool_ids = tool_ids or list(tools_mod.TOOL_KEYS)
    entries = []
    for tid in tool_ids:
        if tid in tools_mod.TOOLS:
            entries.append({"id": tid, **dict(tools_mod.TOOLS[tid])})
    return yaml.safe_dump(entries, sort_keys=False, default_flow_style=False).strip()


def render_body_yaml(body):
    body = body or {}
    act_ids = body.get("actuators") or list(actuators_mod.ACTUATOR_KEYS)
    params = body.get("parameters") or parameters_mod.default_parameters()

    acts = []
    for aid in act_ids:
        if aid in actuators_mod.ACTUATORS:
            a = actuators_mod.ACTUATORS[aid]
            acts.append({"id": aid, "what": a.get("what"), "effect": a.get("effect")})

    param_entries = []
    for key in parameters_mod.ATTRIBUTE_KEYS:
        param_entries.append(
            {
                "id": key,
                "label": parameters_mod.ATTRIBUTE_LABELS.get(key),
                "value": params.get(key, 1),
                "what": parameters_mod.ATTRIBUTE_DESCRIPTIONS.get(key),
                "effect": parameters_mod.ATTRIBUTE_EFFECTS.get(key),
            }
        )

    doc = {"actuators": acts, "parameters": param_entries}
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False).strip()
