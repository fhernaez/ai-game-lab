from app.domain.volleyball import attributes, rules
from app.extensions import db
from app.models import Event, Match, Player, Team, User


def _make_user(username, password="secret"):
    user = User(username=username, email=f"{username}@example.com", role="student")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_seed_creates_admin(app):
    with app.app_context():
        assert User.query.filter_by(username="admin").first() is not None


def test_register_and_login(client):
    client.post(
        "/auth/register",
        data={"username": "bob", "email": "bob@example.com", "password": "secret"},
        follow_redirects=True,
    )
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login", data={"username": "bob", "password": "secret"}, follow_redirects=True
    )
    assert b"Matchmaking" in resp.data


def test_volleyball_rules():
    assert rules.set_target(1) == 21
    assert rules.set_target(3) == 15
    assert rules.is_set_won(21, 10, 1) is True
    assert rules.is_set_won(21, 20, 1) is False  # no 2-point margin
    assert rules.switch_interval(3) == 5


def test_attributes_and_budget():
    assert attributes.difficulty_budget("easy") == 45
    assert attributes.difficulty_budget("hard") == 12
    a = {"jumping_height": 8, "transition_speed": 1, "receiving_accuracy": 1,
         "passing_accuracy": 1, "shoot_accuracy_distance": 1,
         "shoot_accuracy_power": 1, "shoot_max_power": 1}
    assert attributes.attributes_cost(a) == 7
    arch = attributes.archetype_attributes("tower")
    assert arch["jumping_height"] == 8
    assert attributes.slider_to_float(10) == 1.0
    assert attributes.slider_to_float(1) == 0.1


def test_team_config_saves(app, client):
    with app.app_context():
        bob = _make_user("bob")
        alice = _make_user("alice")
        bob_id, alice_id = bob.id, alice.id

    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"difficulty": "medium"})
    with app.app_context():
        match = Match.query.order_by(Match.id.desc()).first()
        mid = match.id
        team = Team.query.filter_by(match_id=mid, player_id=bob_id).first()
        p = Player.query.filter_by(team_id=team.id, slot=1).first()
        pid = p.id

    client.post(
        f"/matches/{mid}/team",
        data={
            "strategy": "serve deep",
            f"attr_{pid}_jumping_height": "8",
            f"attr_{pid}_transition_speed": "3",
            f"attr_{pid}_receiving_accuracy": "4",
            f"attr_{pid}_passing_accuracy": "4",
            f"attr_{pid}_shoot_accuracy_distance": "3",
            f"attr_{pid}_shoot_accuracy_power": "6",
            f"attr_{pid}_shoot_max_power": "8",
            f"model_{pid}": "mock:mock-model",
            f"temperature_{pid}": "0.5",
            f"max_tokens_{pid}": "300",
            f"top_p_{pid}": "0.9",
            f"frequency_penalty_{pid}": "0.1",
            f"presence_penalty_{pid}": "0.2",
            f"response_format_{pid}": "json",
        },
    )
    with app.app_context():
        p = db.session.get(Player, pid)
        cfg = p.configuration_json
        assert cfg["attributes"]["jumping_height"] == 8
        assert cfg["model"] == "mock:mock-model"
        assert cfg["temperature"] == 0.5


def test_full_match_flow(app, client):
    with app.app_context():
        _make_user("bob")
        _make_user("alice")

    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"difficulty": "medium"})
    with app.app_context():
        match = Match.query.order_by(Match.id.desc()).first()
        mid = match.id
        assert match.status == "created"

    client.post(f"/matchmaking/{mid}/invite", data={"username": "alice"})
    with app.app_context():
        assert db.session.get(Match, mid).status == "invited"

    client.get("/auth/logout")
    client.post("/auth/login", data={"username": "alice", "password": "secret"})
    client.post(f"/matchmaking/{mid}/accept")
    client.post(f"/matches/{mid}/ready")

    client.get("/auth/logout")
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post(f"/matches/{mid}/ready")

    with app.app_context():
        match = db.session.get(Match, mid)
        assert match.status == "finished"
        assert match.final_state_json is not None
        types = {e.event_type for e in Event.query.filter_by(match_id=mid).all()}
        assert "DECISION" in types
        assert "POINT" in types
        assert "MATCH_FINISHED" in types


def test_match_delete_cascades(app, client):
    with app.app_context():
        _make_user("bob")
        _make_user("alice")

    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"difficulty": "easy"})
    with app.app_context():
        mid = Match.query.order_by(Match.id.desc()).first().id
    client.post(f"/matches/{mid}/delete")
    with app.app_context():
        assert db.session.get(Match, mid) is None
        assert Team.query.filter_by(match_id=mid).count() == 0
        assert Event.query.filter_by(match_id=mid).count() == 0


def test_start_match_does_not_reenqueue(app):
    from unittest.mock import patch

    from app.application import match_service
    from app.models import Match

    with app.app_context():
        m = Match(host_id=1, guest_id=2, status="queued", difficulty="medium", seed=1)
        db.session.add(m)
        db.session.commit()
        with patch.object(match_service, "enqueue") as mock_enqueue:
            match_service.start_match(m)
        mock_enqueue.assert_not_called()
        assert m.status == "queued"


def test_engine_streams_events(app):
    from app.domain.volleyball.attributes import default_attributes
    from app.domain.volleyball.engine import MatchEngine
    from app.infrastructure.llm.mock import MockLLMProvider

    collected = []

    def resolve(ref):
        return MockLLMProvider(), "mock-model"

    teams = []
    for ti in range(2):
        players = [
            {
                "slot": s,
                "name": f"P{s}",
                "attributes": {k: 5 for k in default_attributes()},
                "model": "",
                "params": {},
                "instructions": "",
            }
            for s in (1, 2)
        ]
        teams.append({"name": f"T{ti}", "instructions": "", "players": players})

    engine = MatchEngine(teams, resolve, seed=1)
    _events, _state, _usages = engine.run(on_event=collected.append)

    assert len(collected) > 0
    assert collected[0]["event_type"] == "MATCH_STARTED"
    assert any(e["event_type"] == "TRAJECTORY" for e in collected)
    assert any(e["event_type"] == "MATCH_FINISHED" for e in collected)
