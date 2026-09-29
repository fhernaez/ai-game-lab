"""Multi-user matchmaking: invite, accept, decline, ready-up, and crew creation."""

from ..extensions import db
from ..models import Competition, Crew, CrewMember
from . import competition_service, crew_service


def create_competition(host, game_version, round_budget=None):
    blueprint = game_version.blueprint_json
    budget = round_budget or blueprint["competition"].get("default_round_budget", 6)
    competition = Competition(
        game_version_id=game_version.id,
        host_id=host.id,
        status="created",
        round_budget=budget,
        wall_clock_timeout=blueprint["competition"].get("wall_clock_timeout_seconds", 600),
        configuration_json={"game_id": blueprint["game"]["id"]},
    )
    db.session.add(competition)
    db.session.flush()
    _create_crew(competition, host, blueprint)
    db.session.commit()
    return competition


def invite(competition, guest):
    competition.guest_id = guest.id
    competition.status = "invited"
    db.session.commit()


def accept(competition, guest):
    if competition.guest_id != guest.id:
        raise ValueError("This invitation is not for you.")
    blueprint = competition.game_version.blueprint_json
    _create_crew(competition, guest, blueprint)
    competition.status = "accepted"
    db.session.commit()


def decline(competition, guest):
    if competition.guest_id == guest.id:
        competition.status = "declined"
        db.session.commit()


def mark_ready(competition, user):
    if user.id == competition.host_id:
        competition.host_ready = True
    elif user.id == competition.guest_id:
        competition.guest_ready = True
    db.session.commit()
    if competition.host_ready and competition.guest_ready:
        competition_service.start_competition(competition)


def cancel(competition, user):
    if user.id in (competition.host_id, competition.guest_id):
        if competition.status in ("created", "invited", "accepted"):
            competition.status = "cancelled"
            db.session.commit()


def _create_crew(competition, player, blueprint):
    crew = Crew(
        competition_id=competition.id,
        player_id=player.id,
        name=f"{player.username}'s Crew",
        configuration_json=crew_service.default_crew_configuration(),
    )
    db.session.add(crew)
    db.session.flush()
    for role in crew_service.roles_for_blueprint(blueprint):
        db.session.add(
            CrewMember(
                crew_id=crew.id,
                role=role["id"],
                speak_order=role.get("speak_order", 0),
                is_speaker=bool(role.get("speaker", False)),
                configuration_json=crew_service.default_member_configuration(blueprint, role["id"]),
            )
        )
    return crew
