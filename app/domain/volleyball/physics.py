"""Simplified stochastic physics for beach volleyball.

All randomness uses a seeded `random.Random` so a match is reproducible.
Skill values are sliders 1..10 mapped to 0.1..1.0 via attributes.slider_to_float.
"""

import random

from . import rules
from .attributes import slider_to_float


def _f(attrs, key):
    return slider_to_float(attrs.get(key, 1))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def resolve_serve(attrs, power, target, rng):
    """Return (landing, fault) where fault is None or a fault reason."""
    power = _clamp(power, 0.0, 1.0)
    acc_power = _f(attrs, "shoot_accuracy_power")
    acc_dist = _f(attrs, "shoot_accuracy_distance")

    # Low power raises net risk; high power raises spread.
    net_risk = max(0.0, 0.20 - power * 0.2)
    if rng.random() < net_risk:
        return None, "net"

    sigma = (1.0 - acc_power) * power * 1.5 + (1.0 - acc_dist) * 0.4 + 0.1
    x = _clamp(target[0] + rng.gauss(0, sigma), 0, rules.COURT_WIDTH)
    y = _clamp(target[1] + rng.gauss(0, sigma), 0, rules.COURT_LENGTH)
    if not rules.in_bounds(x, y):
        return None, "out"
    return (x, y), None


def resolve_attack(attrs, power, target, rng):
    """A spike/place from the front court over the net."""
    power = _clamp(power, 0.0, 1.0)
    acc_power = _f(attrs, "shoot_accuracy_power")
    acc_dist = _f(attrs, "shoot_accuracy_distance")
    jump = _f(attrs, "jumping_height")

    # A hard attack with poor control flies wide; distance aiming matters for places.
    sigma = (1.0 - acc_power) * power * 2.2 + (1.0 - acc_dist) * 0.5 + 0.1
    net_risk = max(0.0, (1.0 - jump) * 0.25 * power)
    if rng.random() < net_risk:
        return None, "net"

    x = _clamp(target[0] + rng.gauss(0, sigma), 0, rules.COURT_WIDTH)
    y = _clamp(target[1] + rng.gauss(0, sigma), 0, rules.COURT_LENGTH)
    if not rules.in_bounds(x, y):
        return None, "out"
    return (x, y), None


def resolve_receive(attrs, distance, rng):
    """Return True if the player reaches and controls the ball."""
    speed = _f(attrs, "transition_speed")
    receive = _f(attrs, "receiving_accuracy")
    reach = 1.0 + speed * 2.5
    if distance > reach:
        return False
    return rng.random() < (0.3 + 0.7 * receive)


def resolve_set(attrs, distance, rng):
    """Return (success, x_offset) for a set toward the net."""
    accuracy = _f(attrs, "passing_accuracy") * _clamp(1.0 - distance / 8.0, 0.2, 1.0)
    success = rng.random() < (0.4 + 0.6 * accuracy)
    offset = rng.gauss(0, (1.0 - accuracy) * 1.2)
    return success, offset
