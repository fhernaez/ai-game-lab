"""Crew configuration helpers: defaults derived from a blueprint."""


def roles_for_blueprint(blueprint):
    return (blueprint.get("crew") or {}).get("roles", [])


def default_member_configuration(blueprint, role):
    skills = sorted((blueprint.get("markdown", {}).get("skills") or {}).keys())
    role_def = next((r for r in roles_for_blueprint(blueprint) if r.get("id") == role), {})
    return {
        "name": role.title(),
        "instructions": "",
        "model": "",
        "temperature": 0.7,
        "max_tokens": 512,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": [],
        "response_format": "json",
        "skills": skills,
        "selected_skills": [],
        "memory": "short",
        "speak_order": role_def.get("speak_order", 0),
        "is_speaker": bool(role_def.get("speaker", False)),
    }


def default_crew_configuration():
    return {"instructions": "", "strategy": ""}
