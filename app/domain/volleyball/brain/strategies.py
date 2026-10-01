"""Brain-level strategy presets (Aggressive / Defensive / Neutral) + admin list.

A **strategy** is a complete game plan: it pre-fills a player's *brain* (persona,
goal, skills, tools, model parameters) **and** a *body* attribute allocation per match
difficulty (easy / medium / hard). Each body allocation stays within the point-buy
budget for its difficulty (`body/parameters.py`), so the same strategy works — with a
weaker or stronger body — at any difficulty level.

The three defaults are seeded here; the admin can add more, stored under the
``strategy_presets`` AppSetting.
"""

import copy

from . import skills, tools
from ..body import parameters

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
        "attributes": {
            "easy": {
                "jumping_height": 10, "transition_speed": 5, "receiving_accuracy": 4,
                "passing_accuracy": 4, "shoot_accuracy_distance": 4,
                "shoot_accuracy_power": 7, "shoot_max_power": 10,
            },
            "medium": {
                "jumping_height": 9, "transition_speed": 3, "receiving_accuracy": 2,
                "passing_accuracy": 2, "shoot_accuracy_distance": 2,
                "shoot_accuracy_power": 5, "shoot_max_power": 9,
            },
            "hard": {
                "jumping_height": 6, "transition_speed": 2, "receiving_accuracy": 1,
                "passing_accuracy": 1, "shoot_accuracy_distance": 1,
                "shoot_accuracy_power": 2, "shoot_max_power": 6,
            },
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
        "attributes": {
            "easy": {
                "jumping_height": 3, "transition_speed": 10, "receiving_accuracy": 10,
                "passing_accuracy": 8, "shoot_accuracy_distance": 5,
                "shoot_accuracy_power": 3, "shoot_max_power": 3,
            },
            "medium": {
                "jumping_height": 2, "transition_speed": 9, "receiving_accuracy": 9,
                "passing_accuracy": 5, "shoot_accuracy_distance": 3,
                "shoot_accuracy_power": 2, "shoot_max_power": 1,
            },
            "hard": {
                "jumping_height": 1, "transition_speed": 5, "receiving_accuracy": 6,
                "passing_accuracy": 3, "shoot_accuracy_distance": 2,
                "shoot_accuracy_power": 1, "shoot_max_power": 1,
            },
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
        "attributes": {
            "easy": {
                "jumping_height": 6, "transition_speed": 6, "receiving_accuracy": 6,
                "passing_accuracy": 6, "shoot_accuracy_distance": 6,
                "shoot_accuracy_power": 6, "shoot_max_power": 6,
            },
            "medium": {
                "jumping_height": 4, "transition_speed": 4, "receiving_accuracy": 4,
                "passing_accuracy": 4, "shoot_accuracy_distance": 4,
                "shoot_accuracy_power": 4, "shoot_max_power": 4,
            },
            "hard": {
                "jumping_height": 3, "transition_speed": 2, "receiving_accuracy": 3,
                "passing_accuracy": 2, "shoot_accuracy_distance": 2,
                "shoot_accuracy_power": 2, "shoot_max_power": 2,
            },
        },
    },
}


def default_strategies():
    """A deep copy of the built-in strategy presets (dict keyed by id)."""
    return copy.deepcopy(DEFAULT_STRATEGIES)


def strategy_attributes(strategy, difficulty):
    """The body attribute allocation for ``difficulty``, or None if not defined."""
    attrs = (strategy or {}).get("attributes") or {}
    return attrs.get(difficulty)


def strategy_attributes_cost(strategy, difficulty):
    """Point-buy cost of a strategy's body allocation for a difficulty."""
    attrs = strategy_attributes(strategy, difficulty)
    if not attrs:
        return 0
    return parameters.attributes_cost(attrs)


def apply_strategy(brain, strategy):
    """Return ``brain`` with the strategy's brain fields merged over it.

    The strategy fills persona, goal, skills, tools, and model parameters; the model
    reference, sensors, and memory are left untouched. The body attributes are applied
    separately via :func:`strategy_attributes`.
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
