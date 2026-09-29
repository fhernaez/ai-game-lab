# Proposed Folder Structure

```text
ai-game-lab/
│
├── README.md
├── ARCHITECTURE.md
├── CODING_AGENT_PROMPT.md
├── EDUCATIONAL_MODEL.md
├── GAME_BLUEPRINT_SPEC.md
├── requirements.txt
│
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
│
├── docker-compose.yml
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── web/
│   │   ├── templates/
│   │   └── static/
│   │
│   ├── blueprints/
│   │   ├── auth/
│   │   ├── settings/
│   │   ├── games/
│   │   ├── matchmaking/
│   │   ├── crews/
│   │   ├── competitions/
│   │   └── replay/
│   │
│   ├── application/
│   │   ├── blueprint_service.py
│   │   ├── compiler_service.py
│   │   ├── importer_service.py
│   │   ├── competition_service.py
│   │   ├── matchmaking_service.py
│   │   ├── presence_service.py
│   │   ├── crew_service.py
│   │   └── resource_service.py
│   │
│   ├── domain/
│   │   ├── dialogue/
│   │   │   ├── runner.py        # the speak → act → referee round loop
│   │   │   └── round.py
│   │   ├── crew/
│   │   │   ├── crew.py
│   │   │   ├── member.py
│   │   │   └── speak_order.py
│   │   ├── referee/
│   │   │   ├── referee.py
│   │   │   └── verdict.py
│   │   ├── game/
│   │   │   ├── state.py
│   │   │   ├── rules.py
│   │   │   ├── actions.py
│   │   │   └── scoring.py
│   │   └── events/
│   │       ├── event.py
│   │       └── event_store.py
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── ollama.py
│   │   │   └── openai_compatible.py
│   │   ├── memory/
│   │   └── queue/
│   │
│   └── models/
│
├── migrations/
│
├── game_templates/
│   ├── debate/
│   └── team_sports/
│
├── skills/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── games/
│
└── docs/
    ├── USER_GUIDE.md
    ├── STARTUP_GUIDE.md
    └── DEVELOPER_GUIDE.md
```

## Important distinction

`game_templates/` contains canonical starting templates.

Student-created games live in persistent storage and are versioned there. The filesystem
representation can be exported/imported but is not the sole database of record.

## Local environment

The application runs inside its own virtual environment. A `.venv/` directory
(gitignored) is created per checkout:

```text
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` at the repository root pins all Python dependencies so the
application runs reproducibly. Docker remains an optional deployment path.
