# Security and Sandbox Rules

This is an educational multi-user application. Never execute arbitrary
student-generated Python.

## Student-generated content may include

- Markdown
- plain text
- structured configuration
- prompts / system prompts
- skill descriptions
- crew instructions
- model parameter values

## Student-generated content must not directly execute

- Python
- shell commands
- SQL
- Docker commands
- arbitrary HTTP requests
- filesystem operations

The Technical view edits YAML/JSON/Markdown only. It is not a path to arbitrary code
execution: YAML/JSON imports pass the same deterministic validation as the compiler,
and Markdown is treated as inert instruction text.

## LLM tools

Crew members and the referee should receive explicit, allowlisted tools.

Example:

```text
read_game_state
read_crew_state
send_crew_message
propose_action
return_verdict      # referee only
```

No unrestricted database tool should be available to any model.

## Referee verdict guard

The referee is an LLM, so its output is untrusted. Every verdict must be:

1. parsed as JSON and schema-validated;
2. checked for boolean `accepted`;
3. clamped to the scoring rules (min/max, valid scoring events);
4. logged with its explanation.

A malformed verdict is rejected and retried or treated as a no-score, never applied
blindly. The referee must never be able to modify the database arbitrarily.

## Prompt injection

Student instructions are data, not system instructions. The runtime must clearly
separate:

- system/platform instructions
- authoritative game rules
- player-authored crew instructions

Player-authored text must never be able to replace platform or referee instructions.

## Competition isolation

Each competition has:

- isolated state
- isolated crew context
- isolated agent memory
- explicit resource budgets

A crew member must never be able to read the opposing crew's private memory or
configuration (except what the game explicitly reveals).

## Per-player ownership (authorization)

- Each crew is owned by exactly one player.
- A player may read and write only their own crew.
- A player may not see the opponent's hidden parameters before the game reveals them.

## Secrets

LLM API keys and database credentials must never be written into game blueprints or
Markdown files. Store secrets in environment variables or a secure configuration
mechanism.
