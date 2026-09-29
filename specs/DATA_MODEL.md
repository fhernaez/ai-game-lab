# Data Model

## User

```text
User
- id
- username
- email
- password_hash
- role            # admin | teacher | student
- last_seen_at    # presence: considered "online" if within a short window
- created_at
- updated_at
```

Roles: `admin`, `teacher`, `student`.

## Game

```text
Game
- id
- owner_id
- name
- description
- status
- current_version_id
- created_at
- updated_at
```

## GameVersion

```text
GameVersion
- id
- game_id
- version
- blueprint_json      # structured, authoritative
- blueprint_files     # generated artifacts (manifest.yaml, *.md, playground.yaml)
- created_at
```

The structured representation is authoritative. Generated files are exportable
artifacts and, through the Technical view, an editable technical surface; edits are
imported back through validation into the structured config.

## Crew (per player team)

```text
Crew
- id
- competition_id     # or playground_id for a reusable preset
- player_id          # the player who owns this crew
- name
- configuration_json # team instructions, strategy, token/memory allocation
- created_at
- updated_at
```

A **Crew** replaces the previous "Team" concept and is owned by one player. In a
competition, two Crews exist (1v1).

## CrewMember (agent)

```text
CrewMember
- id
- crew_id
- role              # from the game blueprint roles
- speak_order       # position within a round's speak phase
- is_speaker        # whether this role proposes the team's action
- configuration_json
- created_at
```

`configuration_json` carries the **full model parameters**:

```text
{
  "name": "Speaker",
  "instructions": "...",        # system prompt / role instructions
  "model": "ollama:llama3.2",   # provider:model reference
  "temperature": 0.7,
  "max_tokens": 512,
  "top_p": 0.9,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "stop": ["\n\n"],
  "response_format": "json",
  "skills": ["argumentation"],
  "selected_skills": ["argumentation"],
  "memory": "short",
  "communication": {"team": true, "referee": "action_only", "opponents": false}
}
```

## Competition

```text
Competition
- id
- game_version_id
- host_id             # the player who created the match
- guest_id            # the invited player (nullable until accepted)
- status              # created | invited | accepted | configuring | ready
                      #   | running | finished | cancelled | declined
- round_budget        # number of dialogue rounds (set at setup)
- wall_clock_timeout  # safety cap in seconds
- configuration_json  # seed, snapshot of crews/roles for the run
- final_state_json
- created_at
- started_at
- finished_at
```

## CrewCompetition (join)

```text
CrewCompetition
- competition_id
- crew_id
- player_id
```

## Invitation / ready state

Modeled as fields on `Competition` (`host_id`, `guest_id`, `status`) rather than a
separate table. `status` transitions encode the invitation lifecycle.

## Event (interaction log)

```text
Event
- id
- competition_id
- sequence_number
- event_type      # ROUND_STARTED, CREW_MESSAGE, ACTION_PROPOSED,
                  # REFEREE_VERDICT, STATE_CHANGED, SCORE_CHANGED, ...
- actor_id
- payload_json    # full trace for dialogue events: prompt, parameters,
                  # raw_response, parsed, tokens, duration_ms
- created_at
```

Dialogue events (`CREW_MESSAGE`, `REFEREE_VERDICT`, `ACTION_PROPOSED`) carry the full
interaction trace in `payload_json` so the log is readable and replayable.

## Action

```text
Action
- id
- competition_id
- round_number
- crew_id
- member_id
- action_type
- request_json     # the structured action proposed
- result_json      # the validated/applied result
- created_at
```

## ResourceUsage

```text
ResourceUsage
- id
- competition_id
- member_id
- tokens_input
- tokens_output
- model
- duration_ms
- created_at
```

## AppSetting

```text
AppSetting
- id
- key              # e.g. "role_defaults", "default_model", "provider_models"
- value            # JSON
```

Used for admin-editable settings: role defaults, the global default model, and the
editable model lists per provider.

---

The exact SQLAlchemy schema is implemented only after the domain objects and workflows
are defined.
