"""The crew dialogue runner: speak → act → referee, round by round."""

import random

from . import events as ev
from . import prompts
from .referee import Referee, apply_guard


class CompetitionCancelled(Exception):
    pass


MESSAGE_TEMPLATES = [
    "shares an observation about the current state",
    "suggests a possible approach",
    "reports relevant information",
    "asks a teammate for confirmation",
    "flags a risk in the current plan",
    "proposes a refinement to the strategy",
]


class DialogueRunner:
    """Executes a bounded dialogue between two crews and a referee model."""

    def __init__(self, blueprint, resolve, referee, seed=0):
        self.blueprint = blueprint
        self.resolve = resolve      # resolve(model_ref) -> (provider, model_name)
        self.referee = referee      # Referee instance
        self.rng = random.Random(seed)

    def run(self, crews, should_stop=None):
        events = []
        usages = []
        state = {"scores": {c.name: 0 for c in crews}, "round": 0}

        round_budget = int(
            (self.blueprint.get("competition") or {}).get("default_round_budget", 6)
        )

        events.append(ev.make_event(ev.GAME_STARTED, payload={"state": state}))

        for r in range(1, round_budget + 1):
            if should_stop and should_stop():
                raise CompetitionCancelled()
            state["round"] = r
            events.append(ev.make_event(ev.ROUND_STARTED, payload={"round": r}))

            for crew in crews:
                self._crew_turn(crew, r, state, events, usages)

            events.append(ev.make_event(ev.ROUND_FINISHED, payload={"round": r}))

        events.append(ev.make_event(ev.GAME_FINISHED, payload={"state": state}))
        return events, state, usages

    def _crew_turn(self, crew, round_number, state, events, usages):
        allowed = self._allowed_actions()

        # --- SPEAK: each member produces one message in speak order ---
        round_messages = []
        for member in crew.members_in_order():
            provider, model = self.resolve(member.model)
            messages = prompts.build_member_prompt(
                self.blueprint, crew, member, state, round_messages, allowed
            )
            mock_output = {
                "message": self._make_message(member, round_number)
            }
            result = provider.complete(
                messages,
                model=model,
                mock_output=mock_output,
                **member.params,
            )
            parsed = result.parse_json(default={"message": ""})
            message_text = (
                parsed.get("message")
                if isinstance(parsed, dict)
                else str(parsed)
            )
            events.append(
                ev.make_event(
                    ev.CREW_MESSAGE,
                    actor_id=member.role,
                    round=round_number,
                    crew=crew.name,
                    role=member.role,
                    prompt=messages,
                    params=member.params,
                    raw=result.content,
                    parsed=parsed,
                    tokens_input=result.tokens_input,
                    tokens_output=result.tokens_output,
                    model=result.model or model,
                )
            )
            usages.append(self._usage(member.role, result, model))
            round_messages.append({"role": member.role, "content": message_text})

        # --- ACT: the speaker proposes a structured action ---
        speaker = crew.speaker()
        provider, model = self.resolve(speaker.model)
        action = self._propose(
            crew, speaker, state, round_messages, allowed, events, round_number, usages
        )

        # --- REFEREE: verdict + guard ---
        mock_verdict = self._mock_verdict()
        raw, parsed_verdict, result = self.referee.evaluate(
            self.blueprint, action, state, round_messages, mock_output=mock_verdict
        )
        verdict = apply_guard(self.blueprint, parsed_verdict)
        events.append(
            ev.make_event(
                ev.REFEREE_VERDICT,
                actor_id="referee",
                round=round_number,
                crew=crew.name,
                action=action,
                raw=raw,
                parsed=parsed_verdict,
                verdict=verdict.to_dict(),
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                model=result.model or model,
            )
        )
        usages.append(self._usage("referee", result, model))

        if verdict.accepted and verdict.score:
            state["scores"][crew.name] += verdict.score
            events.append(
                ev.make_event(
                    ev.SCORE_CHANGED,
                    actor_id="referee",
                    crew=crew.name,
                    delta=verdict.score,
                    explanation=verdict.explanation,
                    state=dict(state),
                )
            )
        events.append(
            ev.make_event(
                ev.STATE_CHANGED,
                actor_id="referee",
                crew=crew.name,
                state=dict(state),
            )
        )

    def _allowed_actions(self):
        actions = (self.blueprint.get("dialogue") or {}).get("actions") or []
        return [a.get("id") for a in actions if a.get("id")]

    def _make_message(self, member, round_number):
        template = self.rng.choice(MESSAGE_TEMPLATES)
        return f"{member.role} (round {round_number}) {template}"

    def _propose(self, crew, speaker, state, round_messages, allowed, events, rnd, usages):
        provider, model = self.resolve(speaker.model)
        messages = prompts.build_speaker_prompt(
            self.blueprint, crew, speaker, state, round_messages, allowed
        )
        chosen = self.rng.choice(allowed) if allowed else "NOOP"
        mock_output = {"action": chosen}
        result = provider.complete(
            messages,
            model=model,
            mock_output=mock_output,
            **speaker.params,
        )
        parsed = result.parse_json(default={"action": chosen})
        if not isinstance(parsed, dict) or "action" not in parsed:
            parsed = {"action": chosen}
        events.append(
            ev.make_event(
                ev.ACTION_PROPOSED,
                actor_id=speaker.role,
                round=rnd,
                crew=crew.name,
                action=parsed,
                raw=result.content,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                model=result.model or model,
            )
        )
        usages.append(self._usage(speaker.role, result, model))
        return parsed

    def _mock_verdict(self):
        return {
            "accepted": True,
            "score": self.rng.randint(0, 5),
            "explanation": "Deterministic referee evaluation.",
        }

    @staticmethod
    def _usage(actor, result, model):
        return {
            "member_id": actor,
            "tokens_input": result.tokens_input,
            "tokens_output": result.tokens_output,
            "model": result.model or model,
            "duration_ms": 0,
        }
