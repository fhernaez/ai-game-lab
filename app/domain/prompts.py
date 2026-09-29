"""Prompt assembly for crew members and the referee.

Prompts are built from controlled sections. Within a round, each crew member's
prompt includes the messages earlier members already produced.
"""


def build_member_prompt(blueprint, crew, member, state, round_messages, allowed_actions):
    markdown = blueprint.get("markdown", {})
    role_md = (markdown.get("agents") or {}).get(member.role, "")
    skills_md = "\n".join(
        markdown.get("skills", {}).get(s, "") for s in member.skills
    )

    system = (
        "You are a member of a crew participating in an educational AI game.\n"
        "You must follow the game rules and only use the information available "
        "to you. Return only structured JSON."
    )

    history = "\n".join(
        f"{m['role']}: {m['content']}" for m in round_messages
    ) or "(no messages yet this round)"

    user = "\n\n".join(
        [
            f"GAME: {blueprint['game'].get('name', '')}",
            "GAME RULES:\n" + markdown.get("rules", ""),
            f"YOUR ROLE: {member.role}\n" + role_md,
            "YOUR SKILLS:\n" + (skills_md or "(none)"),
            f"CREW: {crew.name}",
            "CREW INSTRUCTIONS:\n" + crew.instructions,
            "CURRENT GAME STATE:\n" + _render_state(state),
            "WHAT YOUR CREW HAS SAID SO FAR THIS ROUND:\n" + history,
            "AVAILABLE ACTIONS:\n" + ", ".join(allowed_actions),
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_speaker_prompt(blueprint, crew, member, state, round_messages, allowed_actions):
    """The speaker proposes the crew's structured action."""
    messages = build_member_prompt(
        blueprint, crew, member, state, round_messages, allowed_actions
    )
    messages[-1]["content"] += (
        "\n\nYou are the SPEAKER for your crew. After reading what your crew said, "
        "propose ONE structured action from the available actions."
    )
    return messages


def build_referee_prompt(blueprint, action, state, round_messages):
    markdown = blueprint.get("markdown", {})
    system = (
        "You are the referee of an AI game. Evaluate the proposed action against "
        "the authoritative rules and scoring criteria. Return a structured verdict."
    )
    history = "\n".join(
        f"{m['role']}: {m['content']}" for m in round_messages
    ) or "(no messages this round)"
    user = "\n\n".join(
        [
            "AUTHORITATIVE RULES:\n" + markdown.get("rules", ""),
            "SCORING RULES:\n" + markdown.get("scoring", ""),
            "REFEREE INSTRUCTIONS:\n" + markdown.get("referee", ""),
            "CURRENT STATE:\n" + _render_state(state),
            "ROUND DIALOGUE:\n" + history,
            f"PROPOSED ACTION: {action}",
            'Return JSON: {"accepted": true|false, "score": <int>, "explanation": "<brief>"}',
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _render_state(state):
    return "\n".join(f"{k}: {v}" for k, v in state.items())
