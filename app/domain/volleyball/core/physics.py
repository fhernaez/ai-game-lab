"""Deterministic simulation core for beach volleyball.

The core adds a seeded random component to every shot, computes the ball flight
time from distance and shot power, and simulates whether a player can reach the
ball before it lands. All randomness uses a seeded ``random.Random`` so a match is
reproducible.

The tunable speed/fault constants come from the resolved ``core`` config (see
``core/defaults.py``); each function accepts an optional ``core`` dict and falls
back to the defaults.
"""

import math
import random

from . import defaults, rules
from ..body.parameters import slider_to_float


def _f(attrs, key):
    return slider_to_float(attrs.get(key, 1))


def _c(core):
    return core or defaults.DEFAULTS


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_speed(attrs, core=None):
    """Player sprint speed in m/s from transition_speed."""
    c = _c(core)
    return c["move_speed_base"] + c["move_speed_scale"] * _f(attrs, "transition_speed")


def ball_speed(action, power, attrs, core=None):
    """Ball velocity for a given action (m/s)."""
    c = _c(core)
    power = max(0.0, min(1.0, power))
    if action in ("SPIKE", "PLACE", "SERVE"):
        return c["base_ball_speed"] + c["power_speed_bonus"] * _f(attrs, "shoot_max_power") * power
    return c["base_ball_speed"] * 0.5


def flight_time(origin, target, action, power, attrs, core=None):
    return distance(origin, target) / max(1.0, ball_speed(action, power, attrs, core))


def reach_time(distance_, attrs, core=None):
    """Time (s) for a player to cover a distance on the sand."""
    return distance_ / max(0.5, move_speed(attrs, core))


def can_reach(player_pos, landing, attrs, t_flight, margin=0.1, core=None):
    return reach_time(distance(player_pos, landing), attrs, core) <= t_flight + margin


def offset_sigma(action, power, attrs):
    """Spread (meters) of the random landing offset for a shot."""
    power = max(0.0, min(1.0, power))
    if action in ("SPIKE", "PLACE"):
        acc_power = _f(attrs, "shoot_accuracy_power")
        acc_dist = _f(attrs, "shoot_accuracy_distance")
        return (1.0 - acc_power) * power * 1.8 + (1.0 - acc_dist) * 0.5 + 0.08
    if action == "SERVE":
        return (1.0 - _f(attrs, "shoot_accuracy_power")) * power * 1.2 + 0.15
    if action == "SET":
        return (1.0 - _f(attrs, "passing_accuracy")) * 0.9 + 0.1
    if action == "DIG":
        return (1.0 - _f(attrs, "receiving_accuracy")) * 1.2 + 0.15
    return 0.2


def resolve_shot(action, attrs, power, target, rng, core=None):
    """Return (landing, fault, offset).

    ``landing`` is [x, y]; ``fault`` is None or one of "net"/"out".
    """
    c = _c(core)
    sigma = offset_sigma(action, power, attrs)
    x = target[0] + rng.gauss(0, sigma)
    y = target[1] + rng.gauss(0, sigma)
    offset = math.hypot(x - target[0], y - target[1])

    if action in ("SPIKE", "PLACE"):
        net_risk = max(0.0, (1.0 - _f(attrs, "jumping_height")) * c["net_risk_scale"] * power)
        if rng.random() < net_risk:
            return None, "net", offset
    if action == "SERVE" and rng.random() < max(0.0, c["serve_net_risk_base"] - power * c["serve_net_risk_power"]):
        return None, "net", offset

    x = max(0.0, min(c["court_width"], x))
    y = max(0.0, min(c["court_length"], y))
    if not rules.in_bounds(x, y, core):
        return None, "out", offset
    return [x, y], None, offset
