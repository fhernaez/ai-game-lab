"""Skills: the playbook (what the player knows), rendered into the prompt."""

DEFAULT_SKILLS = [
    {
        "id": "deep_defense",
        "title": "Deep defense",
        "what": "Drop back early and read the hitter's shoulder.",
        "effect": "Lets you dig hard, deep attacks and turn them into controlled passes.",
    },
    {
        "id": "smart_serve",
        "title": "Smart serve",
        "what": "Serve deep with control, not just power.",
        "effect": "Pressures the receiver without giving away free points on faults.",
    },
    {
        "id": "placement_attack",
        "title": "Placement attack",
        "what": "Place the ball into empty sand instead of always swinging hard.",
        "effect": "Scores on accuracy when the defense is deep.",
    },
]


def render_skills(skills):
    """Render a list of skills into a prompt block."""
    if not skills:
        return "(no skills)"
    return "\n".join(f"- {s.get('title', s.get('id', 'skill'))}: {s.get('what', '')}" for s in skills)


def load_default_skills():
    return [dict(s) for s in DEFAULT_SKILLS]


def skills_by_ids(ids):
    """Return the full skill dicts for the given skill ids (order-preserving)."""
    if not ids:
        return []
    by_id = {s["id"]: s for s in DEFAULT_SKILLS}
    return [dict(by_id[i]) for i in ids if i in by_id]
