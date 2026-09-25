"""Prompt assembly: prompts are built from controlled sections (see PROMPT_ARCHITECTURE)."""


def build_agent_messages(blueprint, team, agent, state, allowed_actions, recent_events):
    role = agent["role"]
    markdown = blueprint.get("markdown", {})
    role_md = (markdown.get("agents") or {}).get(role, "")
    skills_md = "\n".join(
        markdown.get("skills", {}).get(s, "") for s in agent.get("skills", [])
    )

    system = (
        "You are an AI agent participating in an educational game.\n"
        "You must follow the game rules and only use the information and "
        "actions available to you. Return only a structured JSON action."
    )

    user_parts = [
        f"GAME: {blueprint['game'].get('name', '')}",
        "GAME RULES:\n" + markdown.get("rules", ""),
        f"YOUR ROLE: {role}\n" + role_md,
        "YOUR SKILLS:\n" + (skills_md or "(none)"),
        f"TEAM: {team['name']}",
        "TEAM INSTRUCTIONS:\n" + team.get("instructions", ""),
        "CURRENT GAME STATE:\n" + _render_state(state),
        "RECENT EVENTS:\n" + "\n".join(f"- {e}" for e in recent_events[-5:]),
        "AVAILABLE ACTIONS:\n" + ", ".join(allowed_actions),
    ]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def build_referee_messages(blueprint, action, state):
    markdown = blueprint.get("markdown", {})
    system = "You are the referee of an AI game. Evaluate the declared action."
    user = "\n\n".join(
        [
            "AUTHORITATIVE RULES:\n" + markdown.get("rules", ""),
            "SCORING RULES:\n" + markdown.get("scoring", ""),
            "REFEREE INSTRUCTIONS:\n" + markdown.get("referee", ""),
            "CURRENT STATE:\n" + _render_state(state),
            f"DECLARED ACTION: {action}",
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _render_state(state):
    lines = []
    for key, value in state.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
