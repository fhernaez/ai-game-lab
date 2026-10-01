"""Brain-level strategy presets (Aggressive / Defensive / Neutral) + admin list.

A **strategy** pre-fills a player's *brain* (persona, goal, skills, tools, and model
parameters) — the tactical counterpart to the body **archetypes** in
``body/parameters.py``, which set the 7 athlete attributes. The three defaults are
seeded here; the admin can add more, stored under the ``strategy_presets`` AppSetting.
"""

import copy

from . import skills, tools

DEFAULT_STRATEGIES = {
    "aggressive": {
        "name": "Aggressive",
        "description": "Attack-first: hard serves and spikes, high risk.",
        "what": "Play to finish the point fast with power.",
        "effect": "Pressures the opponent but commits more faults.",
        "brain": {
            "persona": "A fearless attacker who always looks to finish the point hard.",
            "goal": "Win the point with a fast, powerful attack.",
            "skills": ["smart_serve", "placement_attack"],
            "tools": ["serve", "spike", "place", "block"],
            "params": {"temperature": 0.9},
        },
    },
    "defensive": {
        "name": "Defensive",
        "description": "Defense-first: dig everything, force the error.",
        "what": "Play to keep the ball alive and wait for the opponent's mistake.",
        "effect": "Longer rallies and fewer faults, but less attacking pressure.",
        "brain": {
            "persona": "A patient defender who never gives away free points.",
            "goal": "Keep the ball in play and make the opponent make the error.",
            "skills": ["deep_defense", "smart_serve"],
            "tools": ["serve", "dig", "set", "place"],
            "params": {"temperature": 0.5},
        },
    },
    "neutral": {
        "name": "Neutral",
        "description": "Balanced between attack and defense.",
        "what": "Play all-round and choose the best option for each situation.",
        "effect": "Adaptable, without a strong tactical bias.",
        "brain": {
            "persona": "An all-round player who reads the game and adapts.",
            "goal": "Win the point by choosing the best option.",
            "skills": ["deep_defense", "smart_serve", "placement_attack"],
            "tools": list(tools.TOOL_KEYS),
            "params": {"temperature": 0.7},
        },
    },
}


def default_strategies():
    """A deep copy of the built-in strategy presets (dict keyed by id)."""
    return copy.deepcopy(DEFAULT_STRATEGIES)


def apply_strategy(brain, strategy):
    """Return ``brain`` with the strategy's brain fields merged over it.

    The strategy fills persona, goal, skills, tools, and model parameters; the model
    reference, sensors, and memory are left untouched.
    """
    brain = dict(brain or {})
    spec = (strategy or {}).get("brain", {}) or {}

    if spec.get("persona") is not None:
        brain["persona"] = spec["persona"]
    if spec.get("goal") is not None:
        brain["goal"] = spec["goal"]
    if spec.get("skills") is not None:
        brain["skills"] = skills.skills_by_ids(spec["skills"]) or skills.load_default_skills()
    if spec.get("tools") is not None:
        brain["tools"] = spec["tools"]

    params = dict(brain.get("params") or {})
    params.update(spec.get("params") or {})
    brain["params"] = params
    return brain
