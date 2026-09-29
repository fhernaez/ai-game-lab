from app.extensions import db
from app.models import Competition, Crew, CrewMember, Event, Game, GameVersion, User


def _make_user(username, password="secret"):
    user = User(username=username, email=f"{username}@example.com", role="student")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_seed_creates_admin_and_games(app):
    with app.app_context():
        assert User.query.filter_by(username="admin").first() is not None
        assert Game.query.count() == 2


def test_register_and_login(client):
    resp = client.post(
        "/auth/register",
        data={"username": "bob", "email": "bob@example.com", "password": "secret"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login", data={"username": "bob", "password": "secret"}, follow_redirects=True
    )
    assert b"Matchmaking" in resp.data


def test_verdict_guard_clamps_score():
    from app.domain.referee import apply_guard

    blueprint = {"dialogue": {"scoring": [{"kind": "criteria", "criteria": ["a", "b"], "max": 3}]}}
    verdict = apply_guard(blueprint, {"accepted": True, "score": 999, "explanation": "x"})
    assert verdict.accepted is True
    assert verdict.score == 6  # 2 criteria * max 3


def test_crew_config_persists(app, client):
    with app.app_context():
        bob = _make_user("bob")
        _make_user("alice")
        version = GameVersion.query.first()
        vid = version.id
        bob_id = bob.id

    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"game_version_id": vid, "round_budget": 2})
    with app.app_context():
        comp = Competition.query.order_by(Competition.id.desc()).first()
        cid = comp.id
        crew = Crew.query.filter_by(competition_id=cid, player_id=bob_id).first()
        crew_id = crew.id
        member = CrewMember.query.filter_by(crew_id=crew_id).first()
        mid = member.id

    client.post(
        f"/competitions/{cid}/crew",
        data={
            "crew_instructions": "Be aggressive.",
            f"instructions_{mid}": "Coordinate.",
            f"model_{mid}": "mock:mock-model",
            f"temperature_{mid}": "0.9",
            f"max_tokens_{mid}": "256",
            f"top_p_{mid}": "0.8",
            f"frequency_penalty_{mid}": "0.1",
            f"presence_penalty_{mid}": "0.2",
            f"response_format_{mid}": "json",
        },
    )
    with app.app_context():
        crew = db.session.get(Crew, crew_id)
        assert crew.configuration_json["instructions"] == "Be aggressive."
        member = db.session.get(CrewMember, mid)
        assert member.configuration_json["temperature"] == 0.9
        assert member.configuration_json["model"] == "mock:mock-model"


def test_full_match_flow(app, client):
    with app.app_context():
        bob = _make_user("bob")
        alice = _make_user("alice")
        version = GameVersion.query.first()
        vid = version.id

    # host creates
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"game_version_id": vid, "round_budget": 3})
    with app.app_context():
        comp = Competition.query.order_by(Competition.id.desc()).first()
        cid = comp.id
        assert comp.status == "created"

    # host invites guest
    client.post(f"/matchmaking/{cid}/invite", data={"username": "alice"})
    with app.app_context():
        assert db.session.get(Competition, cid).status == "invited"

    # guest accepts and readies
    client.get("/auth/logout")
    client.post("/auth/login", data={"username": "alice", "password": "secret"})
    client.post(f"/matchmaking/{cid}/accept")
    client.post(f"/competitions/{cid}/ready")

    # host readies -> both ready -> auto-start (synchronous in tests)
    client.get("/auth/logout")
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post(f"/competitions/{cid}/ready")

    with app.app_context():
        comp = db.session.get(Competition, cid)
        assert comp.status == "finished"
        assert comp.final_state_json is not None
        event_types = {e.event_type for e in Event.query.filter_by(competition_id=cid).all()}
        assert "CREW_MESSAGE" in event_types
        assert "REFEREE_VERDICT" in event_types
        assert "SCORE_CHANGED" in event_types


def test_competition_delete_cascades(app, client):
    with app.app_context():
        bob = _make_user("bob")
        alice = _make_user("alice")
        version = GameVersion.query.first()
        vid = version.id

    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"game_version_id": vid, "round_budget": 2})
    with app.app_context():
        comp = Competition.query.order_by(Competition.id.desc()).first()
        cid = comp.id
    client.post(f"/competitions/{cid}/delete")
    with app.app_context():
        assert db.session.get(Competition, cid) is None
        assert Crew.query.filter_by(competition_id=cid).count() == 0
        assert Event.query.filter_by(competition_id=cid).count() == 0
