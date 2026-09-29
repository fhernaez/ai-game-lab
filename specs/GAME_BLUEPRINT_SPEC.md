# Game Blueprint Specification — V2

## Philosophy

The blueprint is the internal contract between the friendly GUI and the generic
dialogue runtime.

Students normally configure it through the GUI, but advanced students may edit it
directly through the always-available Technical view. The GUI generates:

- `manifest.yaml`
- Markdown instruction files
- skill files
- playground permissions

## manifest.yaml

```yaml
game:
  id: example_game
  name: Example Game
  version: 1.0.0
  description: Short description

competition:
  teams: 2                      # 1v1 in V2
  default_round_budget: 6       # default number of dialogue rounds
  wall_clock_timeout_seconds: 600

crew:
  roles:
    - id: trainee
      speak_order: 1
      speaker: true             # this role proposes the team's action
      required: true

    - id: researcher
      speak_order: 2
      speaker: false
      required: true

    - id: speaker
      speak_order: 3
      speaker: false
      required: true

referee:
  enabled: true
  role: referee                 # the referee is a crew member (a model)
  response_format: json         # always a structured verdict

resources:
  team_token_budget: 50000
  team_memory_budget: 12000
  max_concurrent_agents: 3

dialogue:
  actions:
    - id: SUBMIT_ARGUMENT
  scoring:
    - id: debate_score
      kind: criteria
      criteria: [relevance, evidence, response, clarity, compliance]
      max: 5
  win: highest_score

playground:
  editable:
    - crew_instructions
    - member_instructions
    - selected_skills
    - model_selection
    - model_parameters
    - token_distribution
    - memory_distribution

  locked:
    - rules
    - scoring
    - referee
    - action_schema
    - speak_order
```

The `dialogue` block replaces the previous `engine` block. It defines the action schema,
scoring rules (used by the referee verdict guard), and the win condition.

## game.md

Human-readable description of:

- purpose
- educational goals
- game objective
- terminology
- how the dialogue flows

## rules.md

Defines:

- legal actions
- constraints
- speak/act/referee round sequence
- penalties
- winning/final conditions

Rules should be understandable to a student.

## scoring.md

Defines:

- scoring events
- penalties
- bonuses
- tie conditions
- final scoring

These are the bounds the referee verdict guard clamps scores to.

## referee.md

Defines the referee model's role and interpretation instructions, including the
structured verdict format it must return:

```json
{"accepted": true, "score": 3, "explanation": "..."}
```

It must never override the authoritative rule configuration; its verdict is always
schema-validated and clamped by the guard.

## crew-member Markdown

Each role has an instruction file. Recommended sections:

```markdown
# Crew Role

## Identity

## Objective

## Responsibilities

## Speak order

## Tasks

## Skills

## Communication

## Allowed Information

## Restrictions

## Decision Process

## Available Actions

## Output Expectations
```

## skill Markdown

Recommended sections:

```markdown
# Skill

## Name

## Purpose

## What the Agent Learns/Does

## Inputs

## Procedure

## Output

## Limitations
```

## Crew configuration

Each player configures their own crew. The playground must distinguish between:

- editable
- selectable
- fixed

This is essential for fair competitions. Model **parameters** (temperature, top-p,
penalties, max tokens, stop, response format) are editable per crew member when the
game permits it.

## Compiler requirement

The compiler must be deterministic: the same configuration produces semantically
equivalent blueprint files every time.

The compiler should validate before writing:

1. required fields
2. valid roles and speak order
3. valid skills
4. valid models and parameters
5. valid resource limits
6. valid action references
7. valid scoring references
8. valid referee verdict format
9. playground permissions

## Technical view & round-trip

The blueprint files are not read-only artifacts. The Technical view renders them live
and lets advanced students edit them.

Forward direction (GUI → files):

```text
Structured configuration
   |
   v
Validation
   |
   v
Compiler
   |
   +--> manifest.yaml
   +--> game.md
   +--> rules.md
   +--> scoring.md
   +--> referee.md
   +--> agents/*.md
   +--> skills/*.md
   +--> playground.yaml
```

Reverse direction (files → structured configuration):

```text
manifest.yaml / playground.yaml / blueprint JSON
   |
   v
Parser
   |
   v
Validation (same rules as the compiler)
   |
   v
Structured configuration (reconciled)
```

Round-trip rules:

- YAML and JSON are parsed and validated against the same rules as the compiler; on
  success they are reconciled back into the structured configuration, which remains
  authoritative.
- Markdown instruction files (`game.md`, `rules.md`, `scoring.md`, `referee.md`,
  `agents/*.md`, `skills/*.md`) are stored verbatim as authored natural-language text.
- The round-trip must be deterministic.
- On validation failure, nothing is saved and errors are shown inline in the Technical view.
