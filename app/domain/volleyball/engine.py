"""MatchEngine: a time-based, message-driven beach-volleyball match.

Each rally is a serve followed by alternating possessions. On every hit the
deterministic core adds a seeded random offset and computes the ball flight time;
the defending team's players move to intercept, and whichever player reaches the
ball first decides the next shot. The full rally is shared to every agent as
context via their messages.
"""

import random

from . import events as ev
from .body.parameters import slider_to_float
from .brain import decision as decisions
from .brain import tools as brain_tools
from .core import defaults, physics, rules
from .core.world import CourtState

MAX_POSSESSIONS = 40


class MatchCancelled(Exception):
    pass


class _EventSink(list):
    """A list that also forwards each appended event to an optional callback.

    Lets the caller persist/stream events live as the match produces them.
    """

    def __init__(self, on_event=None):
        super().__init__()
        self.on_event = on_event

    def append(self, item):
        super().append(item)
        if self.on_event:
            self.on_event(item)


class MatchEngine:
    def __init__(self, teams, resolve, seed=0, core=None):
        self.teams = teams
        self.resolve = resolve      # resolve(model_ref) -> (provider, model)
        self.core = core or defaults.DEFAULTS
        self.rng = random.Random(seed)
        self.positions = {}
        for ti, team in enumerate(teams):
            for p in team["players"]:
                self.positions[(ti, p["slot"])] = self._home_position(ti, p["slot"])

    def run(self, on_event=None, should_stop=None):
        events = _EventSink(on_event)
        usages = []
        state = CourtState()

        events.append(ev.make_event(ev.MATCH_STARTED, payload=state.to_dict()))

        for _set in range(1, 4):
            if state.winner is not None:
                break
            events.append(ev.make_event(ev.SET_STARTED, set=_set))
            state.current_set = _set
            state.set_points = [0, 0]
            state.touches = 0

            while not rules.is_set_won(*state.set_points, _set, self.core):
                if should_stop and should_stop():
                    raise MatchCancelled()

                events.append(ev.make_event(ev.RALLY_STARTED, payload=state.to_dict()))
                self._play_rally(state, events, usages)

                combined = state.combined_points()
                if combined > 0 and combined % rules.switch_interval(_set, self.core) == 0:
                    state.sides.reverse()
                    events.append(ev.make_event(ev.COURT_SWITCH, payload=state.to_dict()))

            state.set_history.append({"set": _set, "points": list(state.set_points)})
            winner = 0 if state.set_points[0] > state.set_points[1] else 1
            state.sets_won[winner] += 1
            events.append(ev.make_event(ev.SET_WON, set=_set, winner=winner, payload=state.to_dict()))
            if state.sets_won[winner] >= 2:
                state.winner = winner

        state.winner = 0 if state.sets_won[0] > state.sets_won[1] else 1
        events.append(ev.make_event(ev.MATCH_FINISHED, payload=state.to_dict()))
        return events, state.to_dict(), usages

    # -- rally -------------------------------------------------------------
    def _play_rally(self, state, events, usages):
        server_team = state.server
        receiver_team = 1 - server_team
        rally_history = []

        # Everyone returns to their base formation at the start of each rally.
        for ti, team in enumerate(self.teams):
            for p in team["players"]:
                self.positions[(ti, p["slot"])] = self._home_position(ti, p["slot"])

        # SERVE
        server = self._pick_player(server_team, state)
        origin = self._serve_origin(state.sides[server_team])
        # The server steps out behind the end line to serve.
        self.positions[(server_team, server["slot"])] = list(origin)
        decision, _ = self._decide(server_team, server, "SERVE", state, events, usages, rally_history)
        rally_history.append(f"[{server['name']}] {decision['message']}")
        target = self._clamp_to_half(decision["target"], 1 - state.sides[server_team])
        landing, fault, offset = physics.resolve_shot("SERVE", server["attributes"], decision["power"], target, self.rng, self.core)
        state.touches = 0
        if fault:
            state.ball = {"x": 4.0, "y": rules.net_y(self.core), "z": self.core["net_height"]}
            state.flight_time = 0.0
            self._trajectory(events, origin, state.ball, 0.0, offset, server_team, server["slot"])
            self._point(receiver_team, fault, state, events)
            return
        state.ball = {"x": landing[0], "y": landing[1], "z": 0.0}
        state.flight_time = physics.flight_time(origin, landing, "SERVE", decision["power"], server["attributes"], self.core)
        self._trajectory(events, origin, state.ball, state.flight_time, offset, server_team, server["slot"])

        # RALLY (alternating possessions until a ball lands or a fault)
        possession = receiver_team
        for _ in range(MAX_POSSESSIONS):
            result = self._possession(possession, state, events, usages, rally_history)
            if result == "landed":
                self._point(1 - possession, "landed", state, events)
                return
            if result == "block":
                self._point(possession, "block", state, events)
                return
            if result != "over":
                self._point(1 - possession, result, state, events)
                return
            possession = 1 - possession
        self._point(possession, "rally_timeout", state, events)

    def _possession(self, team_index, state, events, usages, rally_history):
        """The defending team tries to return an incoming ball (up to 3 touches).

        Returns "over" (ball sent over the net), "landed" (ball lands in this
        team's court), "block" (clean block), or a fault reason string.
        """
        team = self.teams[team_index]
        own_half = state.sides[team_index]
        opp_half = 1 - own_half
        landing = (state.ball["x"], state.ball["y"])
        t_flight = state.flight_time
        state.touches = 0
        receiver = None

        # BLOCK attempt when the incoming ball is a fast attack.
        if t_flight < self.core["block_max_flight"] and self.rng.random() < self.core["block_attempt_prob"]:
            blocker = self._pick_player(team_index, state)
            bd, _ = self._decide(team_index, blocker, "BLOCK", state, events, usages, rally_history)
            rally_history.append(f"[{blocker['name']}] {bd['message']}")
            jump = slider_to_float(blocker["attributes"]["jumping_height"])
            roll = self.rng.random()
            if roll < self.core["block_clean_prob_scale"] * (jump + self.core["block_clean_jump_offset"]):
                events.append(
                    ev.make_event(ev.BLOCK, team=team_index, team_name=team["name"],
                                  slot=blocker["slot"], result="clean")
                )
                state.touches = 0
                return "block"
            if roll < self.core["block_clean_prob_scale"] * (jump + self.core["block_clean_jump_offset"]) + self.core["block_touch_add"]:
                events.append(
                    ev.make_event(ev.BLOCK, team=team_index, team_name=team["name"],
                                  slot=blocker["slot"], result="touch")
                )
                state.touches = 1
                state.ball = {"x": landing[0],
                              "y": rules.net_y(self.core) - 1.0 if own_half == 0 else rules.net_y(self.core) + 1.0,
                              "z": 2.0}
                receiver = blocker
            else:
                events.append(
                    ev.make_event(ev.BLOCK, team=team_index, team_name=team["name"],
                                  slot=blocker["slot"], result="miss")
                )

        # Touch 1: dig (if no block touch).
        if receiver is None:
            candidates = []
            for p in team["players"]:
                pos = self.positions[(team_index, p["slot"])]
                if physics.can_reach(pos, landing, p["attributes"], t_flight, 0.1, self.core):
                    rt = physics.reach_time(physics.distance(pos, landing), p["attributes"], self.core)
                    candidates.append((rt, p))
            if not candidates:
                return "landed"
            candidates.sort(key=lambda x: x[0])
            receiver = candidates[0][1]
            self.positions[(team_index, receiver["slot"])] = list(landing)
            events.append(
                ev.make_event(
                    ev.INTERCEPT, team=team_index, team_name=team["name"],
                    slot=receiver["slot"], at=landing, time=round(t_flight, 2),
                )
            )
            d1, _ = self._decide(team_index, receiver, "DIG", state, events, usages, rally_history)
            rally_history.append(f"[{receiver['name']}] {d1['message']}")
            state.touches += 1
            # The dig moves the ball from the intercept point toward the setter's area.
            dig_landing = self._clamp_to_half(d1["target"], own_half)
            dig_flight = physics.flight_time(landing, dig_landing, "DIG", d1["power"], receiver["attributes"], self.core)
            state.ball = {"x": dig_landing[0], "y": dig_landing[1], "z": 0.0}
            state.flight_time = dig_flight
            self._trajectory(events, landing, state.ball, dig_flight, 0.0, team_index, receiver["slot"])

        # Touch 2: set (the partner runs to the ball and sets it).
        setter = self._other_player(team_index, receiver)
        self.positions[(team_index, setter["slot"])] = [state.ball["x"], state.ball["y"]]
        d2, _ = self._decide(team_index, setter, "SET", state, events, usages, rally_history)
        rally_history.append(f"[{setter['name']}] {d2['message']}")
        state.touches += 1
        set_point = [4.0, rules.net_y(self.core) - 1.2 if own_half == 0 else rules.net_y(self.core) + 1.2]
        # The set moves the ball from the dig/block-touch point to the attack point.
        set_from = [state.ball["x"], state.ball["y"]]
        set_flight = physics.flight_time(set_from, set_point, "SET", d2["power"], setter["attributes"], self.core)
        state.ball = {"x": set_point[0], "y": set_point[1], "z": 0.0}
        state.flight_time = set_flight
        self._trajectory(events, set_from, state.ball, set_flight, 0.0, team_index, setter["slot"])

        # Touch 3: attack (the attacker runs to the ball and hits it).
        attacker = receiver if self.rng.random() < 0.5 else setter
        self.positions[(team_index, attacker["slot"])] = list(set_point)
        d3, _ = self._decide(team_index, attacker, "SPIKE", state, events, usages, rally_history)
        rally_history.append(f"[{attacker['name']}] {d3['message']}")
        state.touches += 1

        # Four-touch safety guard (the model uses at most 3 touches, but guard).
        if state.touches > 3:
            return "four_touches"

        action = d3["action"] if d3["action"] in ("SPIKE", "PLACE") else "SPIKE"

        # Net touch fault (risk grows with low jumping_height near the net).
        if self.rng.random() < self.core["net_touch_risk"] * (1.0 - slider_to_float(attacker["attributes"]["jumping_height"])):
            return "net_touch"
        # Illegal attack: an open-hand dink (PLACE) is a fault in beach volleyball.
        if action == "PLACE" and self.rng.random() < self.core["illegal_attack_risk"] * (1.0 - slider_to_float(attacker["attributes"]["shoot_accuracy_distance"])):
            return "illegal_attack"

        target = self._clamp_to_half(d3["target"], opp_half)
        landing3, fault, offset = physics.resolve_shot(action, attacker["attributes"], d3["power"], target, self.rng, self.core)
        if fault:
            state.ball = {"x": target[0], "y": rules.net_y(self.core), "z": self.core["net_height"]}
            state.flight_time = 0.0
            self._trajectory(events, set_point, state.ball, 0.0, offset, team_index, attacker["slot"])
            return fault
        state.ball = {"x": landing3[0], "y": landing3[1], "z": 0.0}
        state.flight_time = physics.flight_time(set_point, landing3, action, d3["power"], attacker["attributes"], self.core)
        self._trajectory(events, set_point, state.ball, state.flight_time, offset, team_index, attacker["slot"])
        return "over"

    # -- helpers -----------------------------------------------------------
    def _point(self, team_index, reason, state, events):
        state.set_points[team_index] += 1
        state.touches = 0
        state.server = 1 - team_index
        events.append(ev.make_event(ev.POINT, team=team_index, reason=reason, payload=state.to_dict()))

    def _trajectory(self, events, from_ball, to_ball, flight_time, offset, team, slot):
        if isinstance(from_ball, (list, tuple)):
            from_ball = {"x": from_ball[0], "y": from_ball[1], "z": 0.0}
        events.append(
            ev.make_event(
                ev.TRAJECTORY, from_ball=from_ball, ball=to_ball,
                flight_time=round(flight_time, 2), offset=round(offset, 2),
                team=team, slot=slot,
            )
        )

    def _pick_player(self, team_index, state):
        team = self.teams[team_index]
        idx = (state.combined_points() + state.touches) % len(team["players"])
        return team["players"][idx]

    def _other_player(self, team_index, current):
        team = self.teams[team_index]
        return next(p for p in team["players"] if p["slot"] != current["slot"])

    def _home_position(self, team_index, slot):
        if team_index == 0:
            return [2.5, 3.0] if slot == 1 else [5.5, 5.0]
        return [2.5, 13.0] if slot == 1 else [5.5, 11.0]

    def _clamp_to_half(self, target, half):
        x = max(0.5, min(self.core["court_width"] - 0.5, target[0]))
        if half == 0:
            y = min(target[1], rules.net_y(self.core) - 0.2)
        else:
            y = max(target[1], rules.net_y(self.core) + 0.2)
        return [x, y]

    def _target_in_half(self, half):
        if half == 0:
            y = self.rng.uniform(0.5, rules.net_y(self.core) - 0.5)
        else:
            y = self.rng.uniform(rules.net_y(self.core) + 0.5, self.core["court_length"] - 0.5)
        return [self.rng.uniform(0.5, self.core["court_width"] - 0.5), y]

    def _serve_origin(self, own_half):
        return [4.0, -1.0 if own_half == 0 else self.core["court_length"] + 1.0]

    def _decide(self, team_index, player, action_hint, state, events, usages, rally_history):
        brain = player.get("brain") or {}
        provider, model = self.resolve(brain.get("model") or player.get("model") or "")
        messages = decisions.build_decision_prompt(
            brain, self.teams[team_index]["name"], player["name"], player["slot"],
            state, action_hint, rally_history, team_index
        )
        fallback = self._fallback_decision(action_hint, team_index, state)
        from_pos = list(self.positions.get((team_index, player["slot"]), [4.0, 8.0]))

        error = None
        raw = ""
        tokens_in = tokens_out = 0
        model_used = model
        try:
            result = provider.complete(
                messages, model=model, mock_output=fallback, **brain.get("params", {})
            )
            parsed = result.parse_json(default=fallback)
            decision = decisions.parse_decision(parsed, fallback=fallback)
            raw = result.content
            tokens_in = result.tokens_input
            tokens_out = result.tokens_output
            model_used = result.model or model
        except Exception as exc:
            # A single failed LLM call must not crash the match: fall back to the
            # deterministic decision and record the error for the interaction log.
            decision = dict(fallback)
            error = str(exc)

        # Tool permission check: the action must be one the agent's tools allow.
        allowed = brain_tools.allowed_actions(brain.get("tools")) or list(decisions.ACTIONS)
        if decision["action"] not in allowed:
            decision["action"] = allowed[0]

        # Record the movement destination and speed, then update the tracked position.
        decision.setdefault("move_to", fallback["move_to"])
        decision.setdefault("move_speed", fallback["move_speed"])
        # Constrain the movement to the player's own half (no crossing the net).
        own_half = state.sides[team_index]
        mt = decision["move_to"]
        if own_half == 0:
            mt[1] = max(0.5, min(rules.net_y(self.core) - 0.2, mt[1]))
        else:
            mt[1] = max(rules.net_y(self.core) + 0.2, min(self.core["court_length"] - 0.5, mt[1]))
        decision["move_to"] = mt
        self.positions[(team_index, player["slot"])] = list(mt)

        events.append(
            ev.make_event(
                ev.DECISION,
                actor_id=player["name"],
                team=team_index,
                team_name=self.teams[team_index]["name"],
                slot=player["slot"],
                action_hint=action_hint,
                message=decision.get("message", ""),
                from_pos=from_pos,
                move_to=decision["move_to"],
                move_speed=decision["move_speed"],
                prompt=messages,
                model=model_used,
                params=brain.get("params", {}),
                attributes=player["attributes"],
                raw=raw,
                parsed=decision,
                error=error,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
            )
        )
        usages.append(
            {"member_id": player["name"], "tokens_input": tokens_in, "tokens_output": tokens_out, "model": model_used}
        )
        return decision, error

    def _fallback_decision(self, action_hint, team_index, state):
        target = self._target_in_half(1 - state.sides[team_index])
        own_half = state.sides[team_index]
        net_y = rules.net_y(self.core) - 1.0 if own_half == 0 else rules.net_y(self.core) + 1.0
        speed = self.rng.uniform(0.4, 1.0)
        if action_hint == "SERVE":
            move_to = [4.0, 3.0 if own_half == 0 else 13.0]
            return {"message": "I serve with power to the far corner.", "action": "SERVE",
                    "power": self.rng.uniform(0.5, 0.9), "target": target,
                    "move_to": move_to, "move_speed": speed}
        if action_hint == "DIG":
            move_to = [state.ball["x"], state.ball["y"]]
            return {"message": "I dig and keep the ball alive.", "action": "DIG",
                    "power": 0.3, "target": [4.0, net_y],
                    "move_to": move_to, "move_speed": speed}
        if action_hint == "SET":
            return {"message": "I set a clean ball to the net.", "action": "SET",
                    "power": 0.3, "target": [4.0, net_y],
                    "move_to": [4.0, net_y], "move_speed": speed}
        if action_hint == "BLOCK":
            return {"message": "I jump to block at the net.", "action": "BLOCK",
                    "power": 0.5, "target": [4.0, rules.net_y(self.core)],
                    "move_to": [4.0, net_y], "move_speed": speed}
        action = "SPIKE" if self.rng.random() < 0.6 else "PLACE"
        verb = "spike hard" if action == "SPIKE" else "place a soft shot"
        return {"message": f"I {verb} to the open court.", "action": action,
                "power": self.rng.uniform(0.4, 1.0), "target": target,
                "move_to": [4.0, net_y], "move_speed": speed}
