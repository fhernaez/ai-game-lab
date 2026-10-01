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
- configuration_json   # {"archetype": str|null, "strategy": str, "strategy_preset": str|null}
- created_at
- updated_at
```

A **Team** owns exactly two **Player** agents. (The point-buy cost of a team is
computed from its two players' attribute sliders at validation time, not stored.)
`configuration_json.strategy` is the team's free-text strategy notes (shared to the
engine as `instructions`); `configuration_json.strategy_preset` holds the selected
strategy id. On save, the preset's brain fields (persona, goal, skills, tools, params)
are applied to both players' `brain` config.

## Player (agent)

```text
Player
- id
- team_id          # FK -> teams
- slot             # 1 | 2 (which of the two players)
- configuration_json
- created_at
```

`configuration_json` holds the **brain** and **body** of the agent (see
`AGENT_ARCHITECTURE.md`):

```text
{
  "name": "Player 1",

  "brain": {
    "persona": "A patient defender who reads the game.",
    "goal": "Keep the ball in play and set up the partner.",
    "task": "defend and pass",
    "skills": [
      {"id": "deep_defense", "title": "Deep defense",
       "what": "Drop back early and read the hitter.",
       "effect": "Lets you dig hard, deep attacks."}
    ],
    "tools": ["serve", "dig", "set", "spike", "place", "block"],
    "sensors": ["ball", "own_half", "own_attributes", "rally_history", "score"],
    "memory": {"type": "short_term", "size": 8},
    "model": "ollama:llama3.2",
    "params": {
      "temperature": 0.7,
      "max_tokens": 256,
      "top_p": 1.0,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    }
  },

  "body": {
    "actuators": ["run", "jump", "serve", "pass", "set", "spike", "place", "block", "dig"],
    "parameters": {
      "jumping_height": 5,
      "transition_speed": 5,
      "receiving_accuracy": 5,
      "passing_accuracy": 5,
      "shoot_accuracy_distance": 5,
      "shoot_accuracy_power": 5,
      "shoot_max_power": 5
    }
  }
}
```

The `what`/`effect` strings for the 7 body parameters are the auto-explainable metadata
shown in the GUI. They live once in the central body registry
(`body/parameters.py`), not duplicated per player. The point-buy cost is computed from
`body.parameters[*]` (each slider point above 1 costs 1) at validation time (not stored).

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
- key              # "provider_models", "default_model",
                   #   "core_rules", "core_physics", "core_referee",
                   #   "strategy_presets"
- value            # JSON
```

Used for admin-editable settings: the model list per provider, the global default model,
the three **core** files (rules, physics, referee), and the **strategy presets** that the
admin can edit.

---

The exact SQLAlchemy schema is implemented only after the domain objects and workflows
are defined.
