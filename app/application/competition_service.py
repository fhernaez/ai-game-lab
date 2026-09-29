import random
from datetime import datetime, timezone

from flask import current_app, has_app_context

from ..domain.crew import Crew, CrewMember
from ..domain.dialogue import CompetitionCancelled, DialogueRunner
from ..domain.referee import Referee
from ..extensions import db
from ..infrastructure.llm import get_registry
from ..infrastructure.llm import registry as llm_registry
from ..infrastructure.queue import enqueue
from ..models import Action, Competition, Event, ResourceUsage
from . import settings_service


def _utcnow():
    return datetime.now(timezone.utc)


def start_competition(competition):
    if competition.status in ("running", "finished", "cancelled", "declined"):
        return
    competition.status = "queued"
    db.session.commit()
    enqueue("competitions", run_competition_job, competition.id)


def run_competition_job(competition_id):
    """Entry point for the rq worker (and the synchronous fallback)."""
    if has_app_context():
        _run(competition_id)
    else:
        from app import create_app

        app = create_app()
        with app.app_context():
            _run(competition_id)


def build_crews(competition):
    """Materialize DB crews into domain Crew objects."""
    crews = []
    for db_crew in competition.crews:
        members = []
        for m in db_crew.members:
            cfg = m.configuration_json or {}
            members.append(
                CrewMember(
                    role=m.role,
                    speak_order=m.speak_order,
                    is_speaker=m.is_speaker,
                    config=cfg,
                )
            )
        crews.append(
            Crew(
                name=db_crew.name,
                members=members,
                instructions=(db_crew.configuration_json or {}).get("instructions", ""),
            )
        )
    return crews


def _make_resolver(registry, role_defaults, global_default):
    def resolve(model_ref):
        ref = model_ref or role_defaults.get("__default__") or global_default
        return llm_registry.resolve_model(
            registry,
            ref,
            default_provider=current_app.config.get("DEFAULT_PROVIDER", "mock"),
            default_model=current_app.config.get("DEFAULT_MODEL", "mock-model"),
        )

    return resolve


def _make_referee(registry, role_defaults, global_default):
    ref = role_defaults.get("referee") or global_default
    provider, model = llm_registry.resolve_model(
        registry,
        ref,
        default_provider=current_app.config.get("DEFAULT_PROVIDER", "mock"),
        default_model=current_app.config.get("DEFAULT_MODEL", "mock-model"),
    )
    return Referee(provider, model, params={"temperature": 0.2, "response_format": "json"})


def _should_stop(competition_id):
    def check():
        competition = db.session.get(Competition, competition_id)
        return bool(
            competition
            and (competition.configuration_json or {}).get("cancel_requested")
        )

    return check


def _run(competition_id):
    competition = db.session.get(Competition, competition_id)
    if competition is None:
        return

    blueprint = competition.game_version.blueprint_json
    crews = build_crews(competition)
    seed = (competition.configuration_json or {}).get("seed", 0)

    registry = get_registry()
    role_defaults = settings_service.get_role_defaults()
    global_default = settings_service.get_default_model()

    resolve = _make_resolver(registry, role_defaults, global_default)
    referee = _make_referee(registry, role_defaults, global_default)
    runner = DialogueRunner(blueprint, resolve, referee, seed=seed)

    competition.status = "running"
    competition.started_at = _utcnow()
    db.session.commit()

    try:
        events, final_state, usages = runner.run(crews, should_stop=_should_stop(competition_id))
    except CompetitionCancelled:
        competition.status = "cancelled"
        competition.finished_at = _utcnow()
        db.session.commit()
        return
    except Exception as exc:
        competition.status = "failed"
        competition.finished_at = _utcnow()
        competition.final_state_json = {"error": str(exc)}
        db.session.commit()
        raise

    _persist_events(competition, events)
    _persist_actions(competition, events)
    _persist_usage(competition, usages)

    competition.status = "finished"
    competition.finished_at = _utcnow()
    competition.final_state_json = final_state
    db.session.commit()


def stop_competition(competition):
    if competition.status == "queued":
        competition.status = "cancelled"
        db.session.commit()
        return
    if competition.status == "running":
        config = dict(competition.configuration_json or {})
        config["cancel_requested"] = True
        competition.configuration_json = config
        db.session.commit()


def delete_competition(competition):
    Event.query.filter_by(competition_id=competition.id).delete()
    Action.query.filter_by(competition_id=competition.id).delete()
    ResourceUsage.query.filter_by(competition_id=competition.id).delete()
    for crew in competition.crews:
        from ..models import CrewMember

        CrewMember.query.filter_by(crew_id=crew.id).delete()
    from ..models import Crew

    Crew.query.filter_by(competition_id=competition.id).delete()
    db.session.delete(competition)
    db.session.commit()


def _persist_events(competition, events):
    for seq, event in enumerate(events, start=1):
        db.session.add(
            Event(
                competition_id=competition.id,
                sequence_number=seq,
                event_type=event["event_type"],
                actor_id=event.get("actor_id"),
                payload_json=event.get("payload", {}),
            )
        )
    db.session.flush()


def _persist_actions(competition, events):
    round_number = 0
    for event in events:
        if event["event_type"] == "ROUND_STARTED":
            round_number = event["payload"].get("round", round_number)
        if event["event_type"] == "ACTION_PROPOSED":
            payload = event["payload"]
            action = payload.get("action", {})
            db.session.add(
                Action(
                    competition_id=competition.id,
                    round_number=round_number,
                    crew_id=0,
                    member_id=0,
                    action_type=action.get("action", "") if isinstance(action, dict) else str(action),
                    request_json=action,
                    result_json={"status": "proposed"},
                )
            )
    db.session.flush()


def _persist_usage(competition, usages):
    for usage in usages:
        db.session.add(
            ResourceUsage(
                competition_id=competition.id,
                member_id=usage.get("member_id"),
                tokens_input=usage.get("tokens_input", 0),
                tokens_output=usage.get("tokens_output", 0),
                model=usage.get("model", ""),
                duration_ms=usage.get("duration_ms", 0),
            )
        )
    db.session.flush()


def events_after(competition, after_seq):
    query = Event.query.filter_by(competition_id=competition.id)
    if after_seq:
        query = query.filter(Event.sequence_number > after_seq)
    rows = query.order_by(Event.sequence_number.asc()).all()
    return [
        {
            "sequence_number": e.sequence_number,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "payload": e.payload_json,
        }
        for e in rows
    ]
