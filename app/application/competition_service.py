import random
from datetime import datetime, timezone

from flask import current_app, has_app_context

from ..domain.engine import GameEngine
from ..extensions import db
from ..infrastructure.llm import get_registry
from ..infrastructure.llm import registry as llm_registry
from ..infrastructure.queue import enqueue
from ..models import (
    Action,
    Competition,
    CompetitionTeam,
    Event,
    ResourceUsage,
)
from . import settings_service


def _utcnow():
    return datetime.now(timezone.utc)


def build_teams_snapshot(playground):
    """Materialize teams + agents from a playground into runtime dicts."""
    teams = []
    for team in playground.teams:
        agents = []
        for ac in team.agents:
            cfg = ac.configuration_json or {}
            skills = cfg.get("selected_skills") or cfg.get("skills") or []
            agents.append(
                {
                    "id": f"team{team.id}-agent{ac.id}",
                    "role": ac.role,
                    "name": f"{ac.role.title()}",
                    "skills": skills,
                    "model": cfg.get("model") or "",
                }
            )
        team_cfg = team.configuration_json or {}
        teams.append(
            {
                "name": team.name,
                "instructions": team_cfg.get("instructions", ""),
                "agents": agents,
            }
        )
    return teams


def create_competition(playground, user):
    teams = build_teams_snapshot(playground)
    seed = random.randint(0, 10**9)
    competition = Competition(
        game_version_id=playground.game_version_id,
        status="created",
        configuration_json={
            "game_id": playground.game_version.blueprint_json["game"]["id"],
            "seed": seed,
            "teams": teams,
        },
    )
    db.session.add(competition)
    db.session.flush()

    for team in playground.teams:
        db.session.add(
            CompetitionTeam(
                competition_id=competition.id,
                team_id=team.id,
                player_id=user.id if not user.is_anonymous else None,
            )
        )
    db.session.commit()
    return competition


def enqueue_competition(competition):
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


def _make_resolver(registry, role_defaults, global_default):
    def resolve(agent):
        ref = (
            agent.get("model")
            or role_defaults.get(agent["role"])
            or global_default
        )
        return llm_registry.resolve_model(
            registry,
            ref,
            default_provider=current_app.config.get("DEFAULT_PROVIDER", "mock"),
            default_model=current_app.config.get("DEFAULT_MODEL", "mock-model"),
        )

    return resolve


def _run(competition_id):
    competition = db.session.get(Competition, competition_id)
    if competition is None:
        return

    blueprint = competition.game_version.blueprint_json
    teams = competition.configuration_json["teams"]
    seed = competition.configuration_json.get("seed", 0)

    registry = get_registry()
    role_defaults = settings_service.get_role_defaults()
    global_default = settings_service.get_default_model()
    resolve = _make_resolver(registry, role_defaults, global_default)

    engine = GameEngine(blueprint, resolve, seed=seed)

    competition.status = "running"
    competition.started_at = _utcnow()
    db.session.commit()

    try:
        events, final_state, usages = engine.run(teams)
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
    turn = 0
    for event in events:
        if event["event_type"] == "TURN_STARTED":
            turn = event["payload"].get("iteration", turn)
        if event["event_type"] == "ACTION_DECLARED":
            payload = event["payload"]
            action = payload.get("action", {})
            db.session.add(
                Action(
                    competition_id=competition.id,
                    turn_number=turn,
                    team_id=0,
                    agent_id=event.get("actor_id"),
                    action_type=action.get("action", ""),
                    request_json=action,
                    result_json={"status": "declared"},
                )
            )
    db.session.flush()


def _persist_usage(competition, usages):
    for usage in usages:
        db.session.add(
            ResourceUsage(
                competition_id=competition.id,
                agent_id=usage.get("agent_id"),
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
