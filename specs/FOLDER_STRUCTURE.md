# Proposed Folder Structure (V3)

```text
ai-game-lab/
├── README.md
├── ARCHITECTURE.md
├── VOLLEYBALL_SPEC.md
├── CODING_AGENT_PROMPT.md
├── EDUCATIONAL_MODEL.md
├── DATA_MODEL.md
├── SECURITY_AND_SANDBOX.md
├── FOLDER_STRUCTURE.md
├── PROMPT_ARCHITECTURE.md
├── DEFAULT_PROMPTS.md
├── requirements.txt
│
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── web/
│   │   ├── auth.py users.py settings.py matchmaking.py
│   │   ├── teams.py matches.py history.py api.py
│   │   ├── templates/
│   │   └── static/
│   │       ├── css/app.css
│   │       └── js/volleyball_court.js   # independent simulation module
│   │
│   ├── application/
│   │   ├── matchmaking_service.py
│   │   ├── presence_service.py
│   │   ├── team_service.py      # attributes, point-buy, archetypes, budget
│   │   ├── match_service.py     # create/start/run/stop/delete, history
│   │   ├── settings_service.py  # provider models + default model
│   │   └── seed.py
│   │
│   ├── domain/
│   │   └── volleyball/
│   │       ├── state.py         # CourtState
│   │       ├── rules.py         # win condition, faults, possession, switch
│   │       ├── physics.py       # stochastic serve/flight/defense
│   │       ├── attributes.py    # 7 skills, point-buy, difficulty, archetypes
│   │       ├── decisions.py     # decision protocol + LLM prompt assembly
│   │       ├── engine.py        # MatchEngine
│   │       └── events.py        # event types
│   │
│   ├── infrastructure/
│   │   ├── queue.py             # Redis/rq (sync fallback)
│   │   └── llm/
│   │       ├── base.py
│   │       ├── registry.py
│   │       ├── mock.py
│   │       └── openai_compatible.py
│   │
│   └── models.py
│
├── migrations/
├── tests/
│   ├── conftest.py
│   └── test_app.py
└── docs/
    ├── USER_GUIDE.md
    ├── STARTUP_GUIDE.md
    └── DEVELOPER_GUIDE.md
```

## Local environment

```text
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins all Python dependencies. Docker remains an optional deployment
path.
