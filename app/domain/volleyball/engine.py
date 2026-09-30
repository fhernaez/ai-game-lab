"""MatchEngine: a time-based, message-driven beach-volleyball match.

Each rally is a serve followed by alternating possessions. On every hit the
deterministic core adds a seeded random offset and computes the ball flight time;
the defending team's players move to intercept, and whichever player reaches the
ball first decides the next shot. The full rally is shared to every agent as
context via their messages.
"""

import random

from . import decisions, events as ev, physics, rules
from .state import CourtState

MAX_POSSESSIONS = 40


class MatchCancelled(Exception):
    pass


class MatchEngine:
    def __init__(self, teams, resolve, seed=0):
        self.teams = teams
        self.resolve = resolve      # resolve(model_ref) -> (provider, model)
        self.rng = random.Random(seed)
        self.positions = {}
        for ti, team in enumerate(teams):
            for p in team["players"]:
                self.positions[(ti, p["slot"])] = self._home_position(ti, p["slot"])

    def run(self, should_stop=None):
        events = []
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

            while not rules.is_set_won(*state.set_points, _set):
                if should_stop and should_stop():
                    raise MatchCancelled()

                events.append(ev.make_event(ev.RALLY_STARTED, payload=state.to_dict()))
                self._play_rally(state, events, usages)

                combined = state.combined_points()
                if combined > 0 and combined % rules.switch_interval(_set) == 0:
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

        # SERVE
        server = self._pick_player(server_team, state)
        decision, _ = self._decide(server_team, server, "SERVE", state, events, usages, rally_history)
        rally_history.append(f"[{server['name']}] {decision['message']}")
        target = self._clamp_to_half(decision["target"], 1 - state.sides[server_team])
        origin = self._serve_origin(state.sides[server_team])
        landing, fault, offset = physics.resolve_shot("SERVE", server["attributes"], decision["power"], target, self.rng)
        state.touches = 0
        if fault:
            state.ball = {"x": 4.0, "y": rules.NET_Y, "z": 2.43}
            state.flight_time = 0.0
            self._trajectory(events, origin, state.ball, 0.0, offset, server_team, server["slot"])
            self._point(receiver_team, fault, state, events)
            return
        state.ball = {"x": landing[0], "y": landing[1], "z": 0.0}
        state.flight_time = physics.flight_time(origin, landing, "SERVE", decision["power"], server["attributes"])
        self._trajectory(events, origin, state.ball, state.flight_time, offset, server_team, server["slot"])

        # RALLY (alternating possessions until a ball lands or a fault)
        possession = receiver_team
        for _ in range(MAX_POSSESSIONS):
            result = self._possession(possession, state, events, usages, rally_history)
            if result == "landed":
                self._point(1 - possession, "landed", state, events)
                return
            if result != "over":
                self._point(1 - possession, result, state, events)
                return
            possession = 1 - possession
        self._point(possession, "rally_timeout", state, events)

    def _possession(self, team_index, state, events, usages, rally_history):
        """The defending team tries to return an incoming ball (up to 3 touches)."""
        team = self.teams[team_index]
        own_half = state.sides[team_index]
        opp_half = 1 - own_half
        landing = (state.ball["x"], state.ball["y"])
        t_flight = state.flight_time

        # Which defender reaches the ball before it lands?
        candidates = []
        for p in team["players"]:
            pos = self.positions[(team_index, p["slot"])]
            if physics.can_reach(pos, landing, p["attributes"], t_flight):
                rt = physics.reach_time(physics.distance(pos, landing), p["attributes"])
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

        # Touch 1: receive
        d1, _ = self._decide(team_index, receiver, "DIG", state, events, usages, rally_history)
        rally_history.append(f"[{receiver['name']}] {d1['message']}")
        state.touches += 1

        # Touch 2: set (the partner, always able to reach near the net)
        setter = self._other_player(team_index, receiver)
        d2, _ = self._decide(team_index, setter, "SET", state, events, usages, rally_history)
        rally_history.append(f"[{setter['name']}] {d2['message']}")
        state.touches += 1
        set_point = [4.0, rules.NET_Y - 1.2 if own_half == 0 else rules.NET_Y + 1.2]
        self.positions[(team_index, setter["slot"])] = list(set_point)

        # Touch 3: attack over the net
        attacker = receiver if self.rng.random() < 0.5 else setter
        d3, _ = self._decide(team_index, attacker, "SPIKE", state, events, usages, rally_history)
        rally_history.append(f"[{attacker['name']}] {d3['message']}")
        state.touches += 1
        action = d3["action"] if d3["action"] in ("SPIKE", "PLACE") else "SPIKE"
        target = self._clamp_to_half(d3["target"], opp_half)
        landing3, fault, offset = physics.resolve_shot(action, attacker["attributes"], d3["power"], target, self.rng)
        if fault:
            state.ball = {"x": target[0], "y": rules.NET_Y, "z": 2.43}
            state.flight_time = 0.0
            self._trajectory(events, set_point, state.ball, 0.0, offset, team_index, attacker["slot"])
            return fault
        state.ball = {"x": landing3[0], "y": landing3[1], "z": 0.0}
        state.flight_time = physics.flight_time(set_point, landing3, action, d3["power"], attacker["attributes"])
        self._trajectory(events, set_point, state.ball, state.flight_time, offset, team_index, attacker["slot"])
        return "over"

    # -- helpers -----------------------------------------------------------
    def _point(self, team_index, reason, state, events):
        state.set_points[team_index] += 1
        state.touches = 0
        state.server = 1 - team_index
        events.append(ev.make_event(ev.POINT, team=team_index, reason=reason, payload=state.to_dict()))

    def _trajectory(self, events, from_ball, to_ball, flight_time, offset, team, slot):
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
        x = max(0.5, min(7.5, target[0]))
        if half == 0:
            y = min(target[1], rules.NET_Y - 0.2)
        else:
            y = max(target[1], rules.NET_Y + 0.2)
        return [x, y]

    def _target_in_half(self, half):
        if half == 0:
            y = self.rng.uniform(0.5, rules.NET_Y - 0.5)
        else:
            y = self.rng.uniform(rules.NET_Y + 0.5, rules.COURT_LENGTH - 0.5)
        return [self.rng.uniform(0.5, 7.5), y]

    def _serve_origin(self, own_half):
        return [4.0, 1.0 if own_half == 0 else 15.0]

    def _decide(self, team_index, player, action_hint, state, events, usages, rally_history):
        provider, model = self.resolve(player.get("model") or "")
        messages = decisions.build_decision_prompt(
            self.teams[team_index]["name"], player, state, action_hint, rally_history
        )
        fallback = self._fallback_decision(action_hint, team_index, state)

        error = None
        raw = ""
        tokens_in = tokens_out = 0
        model_used = model
        try:
            result = provider.complete(
                messages, model=model, mock_output=fallback, **player.get("params", {})
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

        events.append(
            ev.make_event(
                ev.DECISION,
                actor_id=player["name"],
                team=team_index,
                team_name=self.teams[team_index]["name"],
                slot=player["slot"],
                action_hint=action_hint,
                message=decision.get("message", ""),
                prompt=messages,
                model=model_used,
                params=player.get("params", {}),
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
        if action_hint == "SERVE":
            return {"message": "I serve with power to the far corner.", "action": "SERVE",
                    "power": self.rng.uniform(0.5, 0.9), "target": target}
        if action_hint == "DIG":
            return {"message": "I dig and keep the ball alive.", "action": "DIG",
                    "power": 0.3, "target": [4.0, rules.NET_Y - 1.0]}
        if action_hint == "SET":
            return {"message": "I set a clean ball to the net.", "action": "SET",
                    "power": 0.3, "target": [4.0, rules.NET_Y - 0.5]}
        action = "SPIKE" if self.rng.random() < 0.6 else "PLACE"
        verb = "spike hard" if action == "SPIKE" else "place a soft shot"
        return {"message": f"I {verb} to the open court.", "action": action,
                "power": self.rng.uniform(0.4, 1.0), "target": target}
