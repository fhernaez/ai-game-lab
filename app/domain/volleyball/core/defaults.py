"""Core configuration: the tunable rules/physics knobs and their defaults.

Each knob carries ``what`` (a definition) and ``effect`` (what it changes on the
game), plus ``min``/``max``/``step`` for the admin form and ``critical`` to mark
parameters that are dangerous to change. The admin's overrides are stored in
AppSettings and merged over these defaults; a match snapshots the resolved values
at start time so history never changes when the rules change.
"""

KNOBS = {
    # -- rules -------------------------------------------------------------
    "net_height": {
        "group": "rules", "value": 2.43, "min": 2.0, "max": 2.6, "step": 0.01,
        "what": "Height of the net in meters.",
        "effect": "A higher net forces higher, riskier hits; a lower net makes spikes easier.",
        "critical": True,
    },
    "court_width": {
        "group": "rules", "value": 8.0, "min": 6.0, "max": 12.0, "step": 0.5,
        "what": "Court width in meters (0..8 by default).",
        "effect": "A wider court gives more open sand to attack and more ground to defend.",
        "critical": True,
    },
    "court_length": {
        "group": "rules", "value": 16.0, "min": 12.0, "max": 20.0, "step": 0.5,
        "what": "Full court length in meters, both halves combined.",
        "effect": "A longer court means longer rallies and more ground to cover.",
        "critical": True,
    },
    "set_target_1": {
        "group": "rules", "value": 21, "min": 5, "max": 30, "step": 1,
        "what": "Points needed to win set 1.",
        "effect": "A lower target shortens the set and rewards early leads.",
        "critical": True,
    },
    "set_target_2": {
        "group": "rules", "value": 21, "min": 5, "max": 30, "step": 1,
        "what": "Points needed to win set 2.",
        "effect": "A lower target shortens the set and rewards early leads.",
        "critical": True,
    },
    "set_target_3": {
        "group": "rules", "value": 15, "min": 5, "max": 30, "step": 1,
        "what": "Points needed to win the tie-breaker set.",
        "effect": "A lower target makes the deciding set quicker.",
        "critical": True,
    },
    "switch_interval_1": {
        "group": "rules", "value": 7, "min": 3, "max": 20, "step": 1,
        "what": "Combined points at which teams switch sides in set 1.",
        "effect": "More frequent switches reduce any side advantage.",
        "critical": False,
    },
    "switch_interval_2": {
        "group": "rules", "value": 7, "min": 3, "max": 20, "step": 1,
        "what": "Combined points at which teams switch sides in set 2.",
        "effect": "More frequent switches reduce any side advantage.",
        "critical": False,
    },
    "switch_interval_3": {
        "group": "rules", "value": 5, "min": 3, "max": 20, "step": 1,
        "what": "Combined points at which teams switch sides in the tie-breaker.",
        "effect": "More frequent switches reduce any side advantage.",
        "critical": False,
    },

    # -- physics -----------------------------------------------------------
    "base_ball_speed": {
        "group": "physics", "value": 11.0, "min": 5.0, "max": 30.0, "step": 0.5,
        "what": "Base ball velocity for a hit (m/s).",
        "effect": "Faster balls give defenders less reaction time.",
        "critical": False,
    },
    "power_speed_bonus": {
        "group": "physics", "value": 9.0, "min": 0.0, "max": 25.0, "step": 0.5,
        "what": "Extra ball velocity added at full spike power.",
        "effect": "Larger bonus makes power attacks much faster than soft touches.",
        "critical": False,
    },
    "move_speed_base": {
        "group": "physics", "value": 1.5, "min": 0.5, "max": 5.0, "step": 0.1,
        "what": "Base sprint speed of every player (m/s).",
        "effect": "Higher base speed makes everyone cover the court faster.",
        "critical": False,
    },
    "move_speed_scale": {
        "group": "physics", "value": 5.5, "min": 0.0, "max": 12.0, "step": 0.1,
        "what": "Extra sprint speed gained at max transition_speed.",
        "effect": "Larger scale rewards high Sand Speed attributes more.",
        "critical": False,
    },
    "net_risk_scale": {
        "group": "physics", "value": 0.25, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "Net-fault risk scale for spike/place, growing with low jump.",
        "effect": "Higher value makes low jumping height cause more net faults.",
        "critical": False,
    },
    "serve_net_risk_base": {
        "group": "physics", "value": 0.18, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "Base chance a soft serve hits the net.",
        "effect": "Higher value makes soft serves riskier.",
        "critical": False,
    },
    "serve_net_risk_power": {
        "group": "physics", "value": 0.15, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "How much serve power reduces the net-fault chance.",
        "effect": "Higher value rewards harder serves with fewer net faults.",
        "critical": False,
    },
    "net_touch_risk": {
        "group": "physics", "value": 0.12, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "Net-touch fault risk for an attacker with low jump.",
        "effect": "Higher value penalizes attacking at the net without jumping height.",
        "critical": False,
    },
    "illegal_attack_risk": {
        "group": "physics", "value": 0.3, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "Fault risk for a soft PLACE (open-hand dink).",
        "effect": "Higher value makes risky dinks with low precision get called more often.",
        "critical": False,
    },
    "block_max_flight": {
        "group": "physics", "value": 0.6, "min": 0.2, "max": 2.0, "step": 0.05,
        "what": "Max incoming flight time that still triggers a block attempt.",
        "effect": "Higher value means defenders try to block slower (loftier) attacks too.",
        "critical": False,
    },
    "block_attempt_prob": {
        "group": "physics", "value": 0.5, "min": 0.0, "max": 1.0, "step": 0.05,
        "what": "Probability a fast incoming attack triggers a block attempt.",
        "effect": "Higher value means more block attempts on fast attacks.",
        "critical": False,
    },
    "block_clean_prob_scale": {
        "group": "physics", "value": 0.20, "min": 0.0, "max": 1.0, "step": 0.01,
        "what": "Scale of the clean-block probability vs jumping height.",
        "effect": "Higher value makes high jumpers clean-block more often.",
        "critical": False,
    },
    "block_clean_jump_offset": {
        "group": "physics", "value": 0.2, "min": 0.0, "max": 1.0, "step": 0.05,
        "what": "Baseline added to jumping height in the clean-block roll.",
        "effect": "Higher value gives everyone a slightly better chance to clean-block.",
        "critical": False,
    },
    "block_touch_add": {
        "group": "physics", "value": 0.35, "min": 0.0, "max": 1.0, "step": 0.05,
        "what": "Extra probability a block results in a touch (rather than clean).",
        "effect": "Higher value means more soft blocks that keep the ball in play.",
        "critical": False,
    },
}

DEFAULTS = {key: spec["value"] for key, spec in KNOBS.items()}

REFEREE_MD = """# The Referee (deterministic)

The referee is **not an LLM**. It is a small piece of deterministic code that
applies the rules and physics to every touch of the ball:

1. **Serve** — the server starts behind the end line and hits into the opponent's
   half. A serve that fails to clear the net or lands out is a fault.
2. **Rally** — each team has at most three touches (a block counts as the first).
   The core adds a seeded random offset to every shot, computes the ball flight
   time from distance and power, and simulates whether a defender reaches the
   ball before it lands.
3. **Faults** — net, out, net touch, illegal attack (open-hand dink), and four
   touches all award the point to the opponent.
4. **Scoring** — a ball that lands in the opponent's court scores for the hitter;
   a fault scores for the opponent. Sets are won with a 2-point margin, best of
   three. Teams switch sides at the configured combined-point interval.

All randomness is seeded per match, so a run is reproducible.
"""


def _clamp(key, value):
    spec = KNOBS[key]
    try:
        value = float(value)
    except (TypeError, ValueError):
        return spec["value"]
    value = max(spec["min"], min(spec["max"], value))
    if isinstance(spec["value"], int):
        value = int(round(value))
    return value


def effective_core(overrides=None):
    """Return DEFAULTS merged with validated/clamped overrides."""
    core = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key in KNOBS:
            core[key] = _clamp(key, value)
    return core


def net_y(core=None):
    """The net's Y coordinate (mid-court), derived from court_length."""
    return (core or DEFAULTS)["court_length"] / 2.0
