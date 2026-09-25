import random

from . import events as ev
from . import prompts, referee

MESSAGE_TEMPLATES = [
    "shares an observation about the current state",
    "suggests a possible approach",
    "reports relevant information",
    "asks a teammate for confirmation",
    "flags a risk in the current plan",
]


class GameEngine:
    """Generic runtime that executes a game blueprint for a set of teams.

    ``resolve`` is a callable ``resolve(agent_dict) -> (provider, model_name)``
    supplied by the caller (the competition service), so each agent can be
    served by a different LLM provider and model.
    """

    def __init__(self, blueprint, resolve, seed=0):
        self.blueprint = blueprint
        self.resolve = resolve
        self.rng = random.Random(seed)

    def run(self, teams):
        events = []
        usages = []
        state = self._initial_state(teams)

        duration = self.blueprint["competition"]["duration"]
        iterations = duration["value"]

        events.append(ev.make_event(ev.GAME_STARTED, payload={"state": state}))

        for i in range(iterations):
            events.append(
                ev.make_event(ev.TURN_STARTED, payload={"iteration": i + 1, "state": state})
            )
            for team in teams:
                self._team_turn(team, state, events, usages)
            events.append(
                ev.make_event(ev.TURN_FINISHED, payload={"iteration": i + 1, "state": state})
            )

        events.append(ev.make_event(ev.GAME_FINISHED, payload={"state": state}))
        return events, state, usages

    def _initial_state(self, teams):
        return {"scores": {t["name"]: 0 for t in teams}, "round": 0, "turn": 0}

    def _team_turn(self, team, state, events, usages):
        # 1. Internal coordination: every agent emits a message.
        for agent in team["agents"]:
            message = self._make_message(agent)
            events.append(
                ev.make_event(ev.AGENT_MESSAGE, actor_id=agent["id"], message=message)
            )

        # 2. The declaring agent picks and declares a structured action.
        declaring = self._declaring_agent(team)
        allowed = referee.allowed_actions_for(self.blueprint, declaring["role"])
        chosen = self.rng.choice(allowed) if allowed else "NOOP"
        action = self._request_action(declaring, team, state, allowed, chosen)

        events.append(
            ev.make_event(
                ev.ACTION_DECLARED,
                actor_id=declaring["id"],
                action=action,
            )
        )
        usages.append(
            {
                "agent_id": declaring["id"],
                "tokens_input": self._last_tokens_input,
                "tokens_output": self._last_tokens_output,
                "model": self._last_model,
                "duration_ms": 0,
            }
        )

        ok, error = referee.validate_action(self.blueprint, declaring["role"], action)
        if not ok:
            events.append(
                ev.make_event(
                    ev.ACTION_REJECTED, actor_id=declaring["id"], action=action, reason=error
                )
            )
            return

        events.append(
            ev.make_event(ev.ACTION_ACCEPTED, actor_id=declaring["id"], action=action)
        )

        points, explanation = referee.resolve_scoring(
            self.blueprint, action.get("action"), self.rng
        )
        if points:
            state["scores"][team["name"]] += points
            events.append(
                ev.make_event(
                    ev.SCORE_CHANGED,
                    actor_id=declaring["id"],
                    team=team["name"],
                    delta=points,
                    explanation=explanation,
                    state=dict(state),
                )
            )
        events.append(
            ev.make_event(
                ev.STATE_CHANGED,
                actor_id=declaring["id"],
                action=action.get("action"),
                state=dict(state),
            )
        )

    def _declaring_agent(self, team):
        declaring_roles = []
        for action in referee.get_actions(self.blueprint):
            roles = action.get("roles") or []
            if len(roles) == 1:
                declaring_roles.append(roles[0])
        by_role = {a["role"]: a for a in team["agents"]}
        for role in declaring_roles:
            if role in by_role:
                return by_role[role]
        trainee = by_role.get("trainee")
        return trainee or team["agents"][0]

    def _make_message(self, agent):
        template = self.rng.choice(MESSAGE_TEMPLATES)
        return f"{agent['role']} {template}"

    def _request_action(self, agent, team, state, allowed, chosen):
        provider, model = self.resolve(agent)

        recent = [f"iteration {state['turn']}"]  # lightweight recent-events stub
        messages = prompts.build_agent_messages(
            self.blueprint,
            {"name": team["name"], "instructions": team.get("instructions", "")},
            {"role": agent["role"], "skills": agent.get("skills", [])},
            state, allowed, recent,
        )
        result = provider.complete(
            messages,
            action_hint={"action": chosen},
            allowed_actions=allowed,
            role=agent["role"],
            seed=self.rng.randint(0, 10**9),
            model=model,
        )
        self._last_tokens_input = result.tokens_input
        self._last_tokens_output = result.tokens_output
        self._last_model = result.model or model
        action = result.parse_json(default={"action": chosen})
        if not isinstance(action, dict) or "action" not in action:
            action = {"action": chosen}
        return action
