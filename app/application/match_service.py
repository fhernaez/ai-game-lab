import random
from datetime import datetime, timezone

from flask import current_app, has_app_context

from ..domain.volleyball.engine import MatchCancelled, MatchEngine
from ..extensions import db
from ..infrastructure.llm import get_registry
from ..infrastructure.llm import registry as llm_registry
from ..infrastructure.queue import enqueue
from ..models import Event, Match, Player, Team
from . import settings_service


def _utcnow():
    return datetime.now(timezone.utc)


def start_match(match):
    if match.status in ("running", "finished", "cancelled", "declined"):
        return
    match.status = "queued"
    db.session.commit()
    enqueue("matches", run_match_job, match.id)


def run_match_job(match_id):
    if has_app_context():
        _run(match_id)
    else:
        from app import create_app

        app = create_app()
        with app.app_context():
            _run(match_id)


def build_teams(match):
    teams = []
    for team in match.teams:
        players = []
        for p in sorted(team.players, key=lambda x: x.slot):
            cfg = p.configuration_json or {}
            players.append(
                {
                    "slot": p.slot,
                    "name": cfg.get("name", f"Player {p.slot}"),
                    "attributes": cfg.get("attributes", {}),
                    "model": cfg.get("model", ""),
                    "params": {
                        k: cfg.get(k)
                        for k in (
                            "temperature", "max_tokens", "top_p",
                            "frequency_penalty", "presence_penalty",
                            "stop", "response_format",
                        )
                        if cfg.get(k) is not None
                    },
                    "instructions": cfg.get("instructions", ""),
                }
            )
        teams.append(
            {
                "name": team.name,
                "instructions": (team.configuration_json or {}).get("strategy", ""),
                "players": players,
            }
        )
    return teams


def _make_resolver(registry, global_default):
    def resolve(model_ref):
        ref = model_ref or global_default
        return llm_registry.resolve_model(
            registry,
            ref,
            default_provider=current_app.config.get("DEFAULT_PROVIDER", "mock"),
            default_model=current_app.config.get("DEFAULT_MODEL", "mock-model"),
        )

    return resolve


def _run(match_id):
    match = db.session.get(Match, match_id)
    if match is None:
        return

    teams = build_teams(match)
    registry = get_registry()
    global_default = settings_service.get_default_model()
    resolve = _make_resolver(registry, global_default)

    engine = MatchEngine(teams, resolve, seed=match.seed or 0)

    match.status = "running"
    match.started_at = _utcnow()
    db.session.commit()

    try:
        events, final_state, usages = engine.run()
    except MatchCancelled:
        match.status = "cancelled"
        match.finished_at = _utcnow()
        db.session.commit()
        return
    except Exception as exc:
        match.status = "failed"
        match.finished_at = _utcnow()
        match.final_state_json = {"error": str(exc)}
        db.session.commit()
        raise

    _persist_events(match, events)

    match.status = "finished"
    match.finished_at = _utcnow()
    match.final_state_json = final_state
    db.session.commit()


def stop_match(match):
    if match.status == "queued":
        match.status = "cancelled"
        db.session.commit()
    elif match.status == "running":
        match.final_state_json = {"cancelled": True}
        match.status = "cancelled"
        db.session.commit()


def delete_match(match):
    Event.query.filter_by(match_id=match.id).delete()
    for team in match.teams:
        Player.query.filter_by(team_id=team.id).delete()
    Team.query.filter_by(match_id=match.id).delete()
    db.session.delete(match)
    db.session.commit()


def history():
    return Match.query.order_by(Match.created_at.desc()).all()


def _persist_events(match, events):
    for seq, event in enumerate(events, start=1):
        db.session.add(
            Event(
                match_id=match.id,
                sequence_number=seq,
                event_type=event["event_type"],
                actor_id=event.get("actor_id"),
                payload_json=event.get("payload", {}),
            )
        )
    db.session.flush()


def events_after(match, after_seq):
    query = Event.query.filter_by(match_id=match.id)
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
