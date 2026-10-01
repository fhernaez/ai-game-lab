from app.domain.volleyball.body import parameters as attributes
from app.domain.volleyball.core import rules
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
        assert cfg["body"]["parameters"]["jumping_height"] == 8
        assert cfg["brain"]["model"] == "mock:mock-model"
        assert cfg["brain"]["params"]["temperature"] == 0.5


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
    from app.domain.volleyball.body.parameters import default_parameters
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
                "attributes": {k: 5 for k in default_parameters()},
                "brain": {},
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


def test_engine_movement_and_faults(app):
    from app.domain.volleyball.body.parameters import default_parameters
    from app.domain.volleyball.engine import MatchEngine
    from app.infrastructure.llm.mock import MockLLMProvider

    def resolve(ref):
        return MockLLMProvider(), "mock-model"

    teams = []
    for ti in range(2):
        players = [
            {"slot": s, "name": f"P{s}", "attributes": {k: 5 for k in default_parameters()}, "brain": {}}
            for s in (1, 2)
        ]
        teams.append({"name": f"T{ti}", "instructions": "", "players": players})

    engine = MatchEngine(teams, resolve, seed=7)
    events, state, _ = engine.run()

    # movement never crosses the net band
    for ev in events:
        if ev["event_type"] == "DECISION":
            y = ev["payload"]["move_to"][1]
            assert not (7.8 < y < 8.2), f"move_to crossed the net: {ev['payload']['move_to']}"

    # the serve starts outside the court
    serve_origins = [
        ev["payload"]["from_ball"]
        for ev in events
        if ev["event_type"] == "TRAJECTORY" and ev["payload"].get("slot") is not None
    ]
    assert any(fb["y"] < 0 or fb["y"] > 16 for fb in serve_origins)

    # block events and fault reasons are present
    assert any(ev["event_type"] == "BLOCK" for ev in events)
    reasons = {ev["payload"].get("reason") for ev in events if ev["event_type"] == "POINT"}
    assert "landed" in reasons


def test_trajectory_from_ball_is_object(app):
    from app.domain.volleyball.body.parameters import default_parameters
    from app.domain.volleyball.engine import MatchEngine
    from app.infrastructure.llm.mock import MockLLMProvider

    def resolve(ref):
        return MockLLMProvider(), "mock-model"

    teams = []
    for ti in range(2):
        players = [
            {"slot": s, "name": f"P{s}", "attributes": {k: 5 for k in default_parameters()}, "brain": {}}
            for s in (1, 2)
        ]
        teams.append({"name": f"T{ti}", "instructions": "", "players": players})

    engine = MatchEngine(teams, resolve, seed=7)
    events, _, _ = engine.run()

    trajs = [ev for ev in events if ev["event_type"] == "TRAJECTORY"]
    assert trajs
    for ev in trajs:
        fb = ev["payload"]["from_ball"]
        assert isinstance(fb, dict), fb
        assert set(("x", "y", "z")) <= set(fb.keys()), fb
        assert isinstance(ev["payload"]["ball"], dict)


def test_engine_resets_formation_each_rally(app):
    from app.domain.volleyball.body.parameters import default_parameters
    from app.domain.volleyball.core.world import CourtState
    from app.domain.volleyball.engine import MatchEngine
    from app.infrastructure.llm.mock import MockLLMProvider

    def resolve(ref):
        return MockLLMProvider(), "mock-model"

    teams = []
    for ti in range(2):
        players = [
            {"slot": s, "name": f"P{s}", "attributes": {k: 5 for k in default_parameters()}, "brain": {}}
            for s in (1, 2)
        ]
        teams.append({"name": f"T{ti}", "instructions": "", "players": players})

    engine = MatchEngine(teams, resolve, seed=3)

    # The sim's home formation must match these exact values.
    assert engine._home_position(0, 1) == [2.5, 3.0]
    assert engine._home_position(0, 2) == [5.5, 5.0]
    assert engine._home_position(1, 1) == [2.5, 13.0]
    assert engine._home_position(1, 2) == [5.5, 11.0]

    state = CourtState()
    state.server = 0
    # Corrupt the tracked positions to simulate pre-fix stale drift.
    for ti in range(2):
        for s in (1, 2):
            engine.positions[(ti, s)] = [99.0, 99.0]

    engine._play_rally(state, [], [])

    # The rally-start reset must have overwritten the corruption.
    for (ti, s), (x, y) in engine.positions.items():
        assert x != 99.0 and y != 99.0, f"player {(ti, s)} not reset: {x}, {y}"


# ---------------------------------------------------------------------------
# Core configuration (admin-editable knobs)
# ---------------------------------------------------------------------------

def test_core_effective_and_clamp(app):
    from app.application import settings_service

    with app.app_context():
        assert settings_service.get_effective_core()["net_height"] == 2.43
        settings_service.set_core_overrides({"net_height": "5"}, {"base_ball_speed": "99"})
        eff = settings_service.get_effective_core()
        assert eff["net_height"] == 2.6  # clamped to max
        assert eff["base_ball_speed"] == 30.0  # clamped to max
        settings_service.reset_core()
        assert settings_service.get_effective_core()["net_height"] == 2.43


def test_rules_honor_core_override():
    from app.domain.volleyball.core import defaults, rules

    core = defaults.effective_core({"set_target_1": 10})
    assert rules.is_set_won(10, 8, 1, core) is True
    assert rules.is_set_won(10, 9, 1, core) is False  # no 2-point margin
    assert rules.set_target(1, core) == 10
    assert rules.net_y({"court_length": 20.0}) == 10.0


def test_physics_honor_core_override():
    from app.domain.volleyball.core import defaults, physics

    core = defaults.effective_core({"base_ball_speed": 20.0, "power_speed_bonus": 0.0})
    attrs = {"shoot_max_power": 1}
    assert physics.ball_speed("SET", 0.5, attrs, core) == 10.0


def test_core_admin_edit_and_restore(app, auth_client):
    from app.application import settings_service

    resp = auth_client.post(
        "/settings/core",
        data={"knob_net_height": "2.5", "knob_set_target_1": "20", "referee_md": "custom referee"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        eff = settings_service.get_effective_core()
        assert eff["net_height"] == 2.5
        assert eff["set_target_1"] == 20
        assert settings_service.get_referee_md() == "custom referee"

    auth_client.post("/settings/core", data={"restore": "1"}, follow_redirects=True)
    with app.app_context():
        assert settings_service.get_effective_core()["net_height"] == 2.43
        assert settings_service.get_referee_md() != "custom referee"


def test_core_readonly_for_student(app, client):
    with app.app_context():
        _make_user("bob")
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    resp = client.get("/settings/core")
    assert resp.status_code == 200
    assert b"read-only access" in resp.data


def test_match_snapshots_core_config(app, client):
    with app.app_context():
        _make_user("bob")
        _make_user("alice")
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"difficulty": "easy"})
    with app.app_context():
        mid = Match.query.order_by(Match.id.desc()).first().id
    client.post(f"/matchmaking/{mid}/invite", data={"username": "alice"})
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
        assert match.core_config_json is not None
        assert match.core_config_json["net_height"] == 2.43


# ---------------------------------------------------------------------------
# Advanced view (read-only agent files) + what/effect
# ---------------------------------------------------------------------------

def test_advanced_view_renders(app, client):
    with app.app_context():
        _make_user("bob")
        _make_user("alice")
    client.post("/auth/login", data={"username": "bob", "password": "secret"})
    client.post("/matchmaking/create", data={"difficulty": "medium"})
    with app.app_context():
        mid = Match.query.order_by(Match.id.desc()).first().id
    resp = client.get(f"/matches/{mid}/advanced")
    assert resp.status_code == 200
    assert b"agent.md" in resp.data
    assert b"body.yaml" in resp.data
    assert b"tools.yaml" in resp.data


def test_agent_and_core_file_render():
    from app.domain.volleyball.brain import render as br
    from app.domain.volleyball.core import render as cr

    brain = {
        "persona": "p",
        "goal": "g",
        "task": "t",
        "model": "m",
        "params": {"temperature": 0.7, "max_tokens": 256, "top_p": 1.0,
                   "frequency_penalty": 0.0, "presence_penalty": 0.0},
    }
    md = br.render_agent_md(brain)
    assert "p" in md and "g" in md

    skills_md = br.render_skills_md([{"id": "deep_defense", "title": "Deep defense", "what": "w", "effect": "e"}])
    assert "Deep defense" in skills_md and "e" in skills_md

    tools_yaml = br.render_tools_yaml(["spike"])
    assert "spike" in tools_yaml and "SPIKE" in tools_yaml

    body_yaml = br.render_body_yaml({"actuators": ["spike"], "parameters": {"jumping_height": 8}})
    assert "jumping_height" in body_yaml

    rules_yaml = cr.render_rules_yaml()
    assert "net_height" in rules_yaml and "net_y" in rules_yaml
    physics_yaml = cr.render_physics_yaml()
    assert "base_ball_speed" in physics_yaml
    assert "referee" in cr.render_referee_md().lower()


def test_brain_permissions_and_prompt():
    from app.domain.volleyball.brain import decision, tools
    from app.domain.volleyball.core.world import CourtState

    assert tools.allowed_actions(None) == []
    assert tools.allowed_actions(["spike"]) == ["SPIKE"]

    brain = {
        "persona": "P",
        "goal": "G",
        "tools": ["spike"],
        "skills": [{"id": "deep_defense", "title": "Deep defense", "what": "w", "effect": "e"}],
        "sensors": ["ball"],
        "model": "m",
        "params": {},
    }
    msgs = decision.build_decision_prompt(brain, "T", "Player 1", 1, CourtState(), "SERVE", [], 0)
    user = msgs[1]["content"]
    assert "Deep defense" in user
    assert "spike" in user
    assert "P" in user and "G" in user


def test_what_effect_present():
    from app.domain.volleyball.body import actuators, parameters
    from app.domain.volleyball.brain import skills, tools
    from app.domain.volleyball.core import defaults

    for key, spec in parameters.ATTRIBUTES.items():
        assert spec["what"] and spec["effect"], key
    for key, spec in actuators.ACTUATORS.items():
        assert spec["what"] and spec["effect"], key
    for key, spec in tools.TOOLS.items():
        assert spec["what"] and spec["effect"], key
    for skill in skills.DEFAULT_SKILLS:
        assert skill["what"] and skill["effect"], skill["id"]
    for key, spec in defaults.KNOBS.items():
        assert spec["what"] and spec["effect"], key


def test_prompt_explains_coordinates():
    from app.domain.volleyball.brain import decision
    from app.domain.volleyball.core.world import CourtState

    brain = {"persona": "", "goal": "", "tools": [], "skills": [], "sensors": [], "params": {}}
    messages = decision.build_decision_prompt(brain, "T", "Player 1", 1, CourtState(), "SERVE", [], 0)
    user = messages[1]["content"]

    assert "COURT COORDINATES" in user
    assert "x = across the court" in user
    assert "net crosses the court at y = 8" in user
    assert "always in the OPPONENT" in user
    assert "always in YOUR half" in user
    # the ball is now labelled x/y/z explicitly
    assert "ball (x=" in user
