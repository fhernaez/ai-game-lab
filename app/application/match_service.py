import random
from datetime import datetime, timezone

from flask import current_app, has_app_context

from ..domain.volleyball.body import parameters
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
    if match.status in ("queued", "running", "finished", "cancelled", "declined"):
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
            brain = cfg.get("brain") or {}
            body = cfg.get("body") or {}
            players.append(
                {
                    "slot": p.slot,
                    "name": cfg.get("name", f"Player {p.slot}"),
                    "attributes": body.get("parameters") or parameters.default_parameters(),
                    "brain": brain,
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
    core = settings_service.get_effective_core()
    engine = MatchEngine(teams, resolve, seed=match.seed or 0, core=core)

    match.status = "running"
    match.started_at = _utcnow()
    match.core_config_json = core
    db.session.commit()

    seq = [0]
    failure = [None]

    def on_event(event):
        # Persist each event immediately so the live view updates in real time.
        seq[0] += 1
        db.session.add(
            Event(
                match_id=match_id,
                sequence_number=seq[0],
                event_type=event["event_type"],
                actor_id=event.get("actor_id"),
                payload_json=event.get("payload", {}),
            )
        )
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            failure[0] = str(exc)
            raise MatchCancelled()

    def should_stop():
        m = db.session.get(Match, match_id)
        return m is None or m.status == "cancelled"

    try:
        _events, final_state, _usages = engine.run(on_event=on_event, should_stop=should_stop)
    except MatchCancelled:
        if failure[0]:
            _finalize(match_id, "failed", {"error": failure[0]})
        else:
            _finalize(match_id, "cancelled")
        return
    except Exception as exc:
        _finalize(match_id, "failed", {"error": str(exc)})
        return

    _finalize(match_id, "finished", final_state)


def _finalize(match_id, status, final_state=None):
    """Safely set the match's final status, tolerating deletion mid-run."""
    match = db.session.get(Match, match_id)
    if match is None:
        db.session.rollback()
        return
    match.status = status
    match.finished_at = _utcnow()
    if final_state is not None:
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
