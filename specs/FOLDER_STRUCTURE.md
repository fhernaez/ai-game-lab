# Proposed Folder Structure (V3)

```text
ai-game-lab/
├── README.md
├── ARCHITECTURE.md
├── AGENT_ARCHITECTURE.md
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
│   │   │   ├── teams/configure.html      # simple view
│   │   │   └── teams/advanced.html       # advanced file view
│   │   └── static/
│   │       ├── css/app.css
│   │       ├── img/players/       # humanoid sprites (idle/run/serve/dig/set/spike/block/jump)
│   │       └── js/sim/            # independent simulation module (court/renderer/replay/live/main/players)
│   │
│   ├── application/
│   │   ├── matchmaking_service.py
│   │   ├── presence_service.py
│   │   ├── team_service.py      # attributes, point-buy, archetypes, budget
│   │   ├── match_service.py     # create/start/run/stop/delete, history
│   │   ├── settings_service.py  # provider models + core files + strategies (admin)
│   │   └── seed.py
│   │
│   ├── domain/
│   │   └── volleyball/
│   │       ├── brain/
│   │       │   ├── agent.py     # BrainAgent (persona, goal, task, skills, tools)
│   │       │   ├── skills.py    # skill registry + prompt injection
│   │       │   ├── strategies.py# brain presets (Aggressive/Defensive/Neutral) + admin list
│   │       │   ├── tools.py     # tool registry + permission check
│   │       │   ├── sensors.py   # perception
│   │       │   ├── memory.py    # short-term memory (rally history)
│   │       │   └── decision.py  # decision protocol + prompt assembly
│   │       ├── body/
│   │       │   ├── body.py      # Body entity
│   │       │   ├── actuators.py # move library
│   │       │   └── parameters.py# 7 attributes + budget + archetypes + what/effect
│   │       ├── core/
│   │       │   ├── rules.py     # win condition, bounds, net, switch
│   │       │   ├── physics.py   # trajectory, flight_time, reach_time
│   │       │   └── world.py     # CourtState (environment)
│   │       ├── engine.py        # orchestrator
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
