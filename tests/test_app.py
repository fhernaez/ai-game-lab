from app.extensions import db
from app.models import Competition, Event, Game, GameVersion, Playground, User


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
    assert b"Games" in resp.data


def test_games_index_requires_login(client):
    resp = client.get("/games")
    assert resp.status_code == 302


def test_game_versions_roundtrip(app):
    from app.application import blueprint_service
    from app.application.importer_service import parse_files
    from app.application.compiler_service import compile_files

    with app.app_context():
        game = Game.query.first()
        version = GameVersion.query.get(game.current_version_id)
        files = compile_files(version.blueprint_json)
        rebuilt = parse_files(files)
        assert rebuilt["game"]["id"] == version.blueprint_json["game"]["id"]
        assert rebuilt["engine"] == version.blueprint_json["engine"]
        assert rebuilt["markdown"]["agents"] == version.blueprint_json["markdown"]["agents"]


def test_invalid_blueprint_rejected(app):
    from app.application.validation import validate_blueprint

    errors = validate_blueprint({"game": {}})
    assert any("game.id" in e for e in errors)


def test_competition_lifecycle(app, auth_client):
    with app.app_context():
        game = Game.query.first()
        version = GameVersion.query.get(game.current_version_id)

        # Create a playground through the UI flow.
        resp = auth_client.post(
            "/playground/create",
            data={"game_version_id": version.id, "name": "Test Playground"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        playground = Playground.query.filter_by(name="Test Playground").first()
        assert playground is not None
        assert len(playground.teams) == 2

        resp = auth_client.post(
            f"/playground/{playground.id}/run", follow_redirects=True
        )
        assert resp.status_code == 200

        competition = Competition.query.order_by(Competition.id.desc()).first()
        assert competition.status == "finished"
        assert competition.final_state_json is not None
        event_count = Event.query.filter_by(competition_id=competition.id).count()
        assert event_count > 0


def test_technical_view_save(app, auth_client):
    from app.application.importer_service import import_files
    from app.application.compiler_service import compile_files

    with app.app_context():
        game = Game.query.first()
        version = GameVersion.query.get(game.current_version_id)
        files = compile_files(version.blueprint_json)

        # Round-trip through the importer to simulate a technical edit save.
        new_blueprint, errors = import_files(files)
        assert errors == []
        new_blueprint["game"]["version"] = "9.9.9"
        from app.application.blueprint_service import save_version

        saved, errors = save_version(game, new_blueprint)
        assert errors == []
        assert saved.version == "9.9.9"


def test_registry_resolve_model(app):
    from app.infrastructure.llm import registry
    from app.infrastructure.llm.mock import MockLLMProvider
    from app.infrastructure.llm.openai_compatible import OpenAICompatibleProvider

    config = {
        "LLM_PROVIDERS": [
            {
                "id": "ollama",
                "type": "openai",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "models": ["llama3.2", "qwen2.5"],
            }
        ],
        "LLM_PROVIDER": "mock",
    }
    reg = registry.build_registry(config)
    assert set(reg.keys()) == {"mock", "ollama"}
    assert isinstance(reg["mock"].provider, MockLLMProvider)
    assert isinstance(reg["ollama"].provider, OpenAICompatibleProvider)
    assert registry.models_for(reg, "ollama") == ["llama3.2", "qwen2.5"]

    provider, model = registry.resolve_model(reg, "ollama:qwen2.5", "mock", "mock-model")
    assert model == "qwen2.5"

    # Bare model names resolve against the default provider.
    provider, model = registry.resolve_model(reg, "mock-model", "mock", "mock-model")
    assert model == "mock-model"
    assert isinstance(provider, MockLLMProvider)

    # Unknown provider falls back to mock.
    provider, model = registry.resolve_model(reg, "nope:x", "mock", "mock-model")
    assert isinstance(provider, MockLLMProvider)


def test_role_defaults_precedence(app):
    from app.application import settings_service

    with app.app_context():
        settings_service.set_role_defaults({"speaker": "ollama:llama3.2"})
        settings_service.set_default_model("mock:mock-model")

        assert settings_service.resolve_agent_model("speaker", "") == "ollama:llama3.2"
        # Explicit agent model wins over role default.
        assert settings_service.resolve_agent_model("speaker", "openai:gpt-4o-mini") == "openai:gpt-4o-mini"
        # Role with no default inherits the global default.
        assert settings_service.resolve_agent_model("attacker", "") == "mock:mock-model"
        # Unknown role without explicit model falls back to global default.
        assert settings_service.resolve_agent_model("unknown", "") == "mock:mock-model"


def test_settings_page_renders(app, auth_client):
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        assert admin.role == "admin"
    resp = auth_client.get("/settings")
    assert resp.status_code == 200
    assert b"Role defaults" in resp.data


def test_run_competition_job_direct(app):
    from app.application import competition_service

    with app.app_context():
        game = Game.query.first()
        version = GameVersion.query.get(game.current_version_id)

        from app.models import Playground, Team, AgentConfiguration
        from app.application import agent_service

        blueprint = version.blueprint_json
        playground = Playground(
            owner_id=User.query.first().id,
            game_version_id=version.id,
            name="Direct Job",
            configuration_json={},
        )
        db.session.add(playground)
        db.session.flush()
        team = Team(
            playground_id=playground.id,
            name="Team A",
            configuration_json=agent_service.default_team_configuration(blueprint),
        )
        db.session.add(team)
        db.session.flush()
        for role_id in agent_service.expand_agents(blueprint):
            db.session.add(
                AgentConfiguration(
                    team_id=team.id,
                    role=role_id,
                    configuration_json=agent_service.default_agent_configuration(blueprint, role_id),
                )
            )
        db.session.commit()

        competition = competition_service.create_competition(
            playground, User.query.first()
        )
        assert competition.status == "created"

        competition_service.enqueue_competition(competition)
        db.session.refresh(competition)
        # No Redis in tests -> runs synchronously and finishes immediately.
        assert competition.status == "finished"
        assert competition.final_state_json is not None
