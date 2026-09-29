"""MatchEngine: runs a full beach-volleyball match (best of 3 sets)."""

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
            events.append(
                ev.make_event(ev.SET_WON, set=_set, winner=winner, payload=state.to_dict())
            )
            if state.sets_won[winner] >= 2:
                state.winner = winner

        state.set_history.append({"sets_won": state.sets_won})
        state.winner = 0 if state.sets_won[0] > state.sets_won[1] else 1
        events.append(ev.make_event(ev.MATCH_FINISHED, payload=state.to_dict()))
        return events, state.to_dict(), usages

    # -- rally -------------------------------------------------------------
    def _play_rally(self, state, events, usages):
        server_team = state.server
        receiver_team = 1 - server_team

        # SERVE
        server = self._pick_player(server_team, state)
        decision, trace = self._decide(server_team, server, "SERVE", state, events, usages)
        landing, fault = physics.resolve_serve(
            server["attributes"], decision["power"], decision["target"], self.rng
        )
        state.touches = 0
        if fault:
            state.ball = {"x": 4.0, "y": 8.0, "z": 2.43}
            self._point(receiver_team, fault, state, events)
            return
        state.ball = {"x": landing[0], "y": landing[1], "z": 0.0}
        events.append(ev.make_event(ev.TOUCH, action="SERVE", team=server_team, ball=state.ball))

        # RALLY (alternating possessions)
        possession = receiver_team
        for _ in range(MAX_POSSESSIONS):
            result = self._possession(possession, state, events, usages)
            if result == "fault":
                self._point(1 - possession, "fault", state, events)
                return
            if result == "out":
                self._point(1 - possession, "out", state, events)
                return
            possession = 1 - possession
        # Safety valve: award a point deterministically.
        self._point(possession, "rally_timeout", state, events)

    def _possession(self, team_index, state, events, usages):
        """One team's 3-touch sequence. Returns 'over' or a fault reason."""
        # Touch 1: dig/receive
        p1 = self._pick_player(team_index, state)
        d1, _ = self._decide(team_index, p1, "DIG", state, events, usages)
        distance = self.rng.uniform(0.5, 4.0)
        if not physics.resolve_receive(p1["attributes"], distance, self.rng):
            return "fault"
        events.append(ev.make_event(ev.TOUCH, action="DIG", team=team_index, ball=state.ball))

        # Touch 2: set
        p2 = self._other_player(team_index, p1)
        d2, _ = self._decide(team_index, p2, "SET", state, events, usages)
        ok, offset = physics.resolve_set(p2["attributes"], self.rng.uniform(1.0, 5.0), self.rng)
        if not ok:
            return "fault"
        events.append(ev.make_event(ev.TOUCH, action="SET", team=team_index, ball=state.ball))

        # Touch 3: attack
        attacker = p1 if self.rng.random() < 0.5 else p2
        d3, _ = self._decide(team_index, attacker, "SPIKE", state, events, usages)
        action = d3["action"] if d3["action"] in ("SPIKE", "PLACE") else "SPIKE"
        target = self._target_in_half(1 - state.sides[team_index], state.sides[team_index])
        landing, fault = physics.resolve_attack(
            attacker["attributes"], d3["power"], d3["target"], self.rng
        )
        if fault:
            return fault
        state.ball = {"x": landing[0], "y": landing[1], "z": 0.0}
        events.append(
            ev.make_event(ev.TOUCH, action=action, team=team_index, ball=state.ball)
        )
        return "over"

    # -- helpers -----------------------------------------------------------
    def _point(self, team_index, reason, state, events):
        state.set_points[team_index] += 1
        state.touches = 0
        state.server = 1 - team_index
        events.append(
            ev.make_event(
                ev.POINT,
                team=team_index,
                reason=reason,
                payload=state.to_dict(),
            )
        )

    def _pick_player(self, team_index, state):
        team = self.teams[team_index]
        # Alternate by rally: use the server state to pick deterministically.
        idx = (state.combined_points() + state.touches) % len(team["players"])
        return team["players"][idx]

    def _other_player(self, team_index, current):
        team = self.teams[team_index]
        return next(p for p in team["players"] if p["slot"] != current["slot"])

    def _target_in_half(self, defending_half, _):
        if defending_half == 0:
            y = self.rng.uniform(0.0, rules.NET_Y)
        else:
            y = self.rng.uniform(rules.NET_Y, rules.COURT_LENGTH)
        return [self.rng.uniform(0.5, 7.5), y]

    def _decide(self, team_index, player, action_hint, state, events, usages):
        provider, model = self.resolve(player.get("model") or "")
        messages = decisions.build_decision_prompt(
            self.teams[team_index]["name"], player, state, action_hint
        )
        fallback = self._fallback_decision(action_hint, team_index, state)
        result = provider.complete(
            messages,
            model=model,
            mock_output=fallback,
            **player.get("params", {}),
        )
        parsed = result.parse_json(default=fallback)
        decision = decisions.parse_decision(parsed, fallback=fallback)
        events.append(
            ev.make_event(
                ev.DECISION,
                actor_id=player["name"],
                team=team_index,
                team_name=self.teams[team_index]["name"],
                slot=player["slot"],
                action_hint=action_hint,
                prompt=messages,
                model=result.model or model,
                params=player.get("params", {}),
                attributes=player["attributes"],
                raw=result.content,
                parsed=decision,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
            )
        )
        usages.append(
            {
                "member_id": player["name"],
                "tokens_input": result.tokens_input,
                "tokens_output": result.tokens_output,
                "model": result.model or model,
            }
        )
        return decision, result

    def _fallback_decision(self, action_hint, team_index, state):
        target = self._target_in_half(1 - state.sides[team_index], state.sides[team_index])
        if action_hint == "SERVE":
            return {"action": "SERVE", "power": self.rng.uniform(0.5, 0.9), "target": target}
        if action_hint == "DIG":
            return {"action": "DIG", "power": 0.3, "target": [4.0, rules.NET_Y - 1.0]}
        if action_hint == "SET":
            return {"action": "SET", "power": 0.3, "target": [4.0, rules.NET_Y - 0.5]}
        action = "SPIKE" if self.rng.random() < 0.6 else "PLACE"
        return {"action": action, "power": self.rng.uniform(0.4, 1.0), "target": target}
