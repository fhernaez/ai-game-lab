"""Multi-user matchmaking: create, invite, accept, decline, ready-up, and team creation."""

import random

from ..extensions import db
from ..models import Match, Player, Team
from . import match_service, team_service


def create_match(host, difficulty):
    difficulty = difficulty if difficulty in ("easy", "medium", "hard") else "medium"
    match = Match(
        host_id=host.id,
        status="created",
        difficulty=difficulty,
        seed=random.randint(0, 10**9),
    )
    db.session.add(match)
    db.session.flush()
    _create_team(match, host, difficulty)
    db.session.commit()
    return match


def invite(match, guest):
    match.guest_id = guest.id
    match.status = "invited"
    db.session.commit()


def accept(match, guest):
    if match.guest_id != guest.id:
        raise ValueError("This invitation is not for you.")
    _create_team(match, guest, match.difficulty)
    match.status = "accepted"
    db.session.commit()


def decline(match, guest):
    if match.guest_id == guest.id:
        match.status = "declined"
        db.session.commit()


def cancel(match, user):
    if user.id in (match.host_id, match.guest_id) and match.status in (
        "created", "invited", "accepted",
    ):
        match.status = "cancelled"
        db.session.commit()


def mark_ready(match, user):
    if user.id == match.host_id:
        match.host_ready = True
    elif user.id == match.guest_id:
        match.guest_ready = True
    db.session.commit()
    if match.host_ready and match.guest_ready:
        match_service.start_match(match)


def _create_team(match, player, difficulty):
    team = Team(
        match_id=match.id,
        player_id=player.id,
        name=f"{player.username}'s Team",
        difficulty=difficulty,
        configuration_json={"strategy": "", "archetype": None},
    )
    db.session.add(team)
    db.session.flush()
    for slot in (1, 2):
        db.session.add(
            Player(
                team_id=team.id,
                slot=slot,
                configuration_json=team_service.default_player_configuration(slot),
            )
        )
    return team
