# Data Model (V3 — Beach Volleyball)

## User

```text
User
- id
- username
- email
- password_hash
- role            # admin | teacher | student
- last_seen_at    # presence
- created_at
- updated_at
```

## Team

```text
Team
- id
- match_id         # FK -> matches
- player_id        # the user who owns this team
- name
- difficulty       # easy | medium | hard (the match's difficulty)
- configuration_json   # {"archetype": str|null, "strategy": str}
- created_at
- updated_at
```

A **Team** owns exactly two **Player** agents. (The point-buy cost of a team is
computed from its two players' attribute sliders at validation time, not stored.)

## Player (agent)

```text
Player
- id
- team_id          # FK -> teams
- slot             # 1 | 2 (which of the two players)
- configuration_json
- created_at
```

`configuration_json`:

```text
{
  "name": "Player 1",
  "attributes": {            # sliders 1-10 (engine maps to 0.1-1.0)
    "jumping_height": 5,
    "transition_speed": 5,
    "receiving_accuracy": 5,
    "passing_accuracy": 5,
    "shoot_accuracy_distance": 5,
    "shoot_accuracy_power": 5,
    "shoot_max_power": 5
  },
  "model": "ollama:llama3.2",   # provider:model
  "temperature": 0.7,
  "max_tokens": 256,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": [],
  "response_format": "json",
  "instructions": ""           # system prompt / strategy
}
```

## Match

```text
Match
- id
- host_id
- guest_id
- status          # created | invited | accepted | ready | running | finished
                  #   | cancelled | declined | failed
- difficulty      # easy | medium | hard
- host_ready
- guest_ready
- final_state_json   # sets, points, winner
- seed            # reproducible randomness
- created_at
- started_at
- finished_at
```

## Event (interaction log)

```text
Event
- id
- match_id
- sequence_number
- event_type      # MATCH_STARTED, SET_STARTED, RALLY_STARTED, DECISION,
                  #   TOUCH, FAULT, POINT, SET_WON, COURT_SWITCH, MATCH_FINISHED
- actor_id
- payload_json    # full trace for DECISION events: prompt, model, model params,
                  #   raw + parsed decision, athlete attributes, physics outcome
- created_at
```

## AppSetting

```text
AppSetting
- id
- key              # "provider_models", "default_model"
- value            # JSON
```

Used for admin-editable settings: the model list per provider and the global default
model.

---

The exact SQLAlchemy schema is implemented only after the domain objects and workflows
are defined.
