# Security and Sandbox Rules

This is an educational multi-user application. Never execute arbitrary
student-generated Python.

## Student-generated content may include

- plain text (team/player instructions, system prompts)
- structured configuration (slider values, model references, model parameters)

## Student-generated content must not directly execute

- Python, shell commands, SQL, Docker commands, arbitrary HTTP requests, filesystem ops

## LLM tools (the sandbox)

Agents are LLM decision-makers with an explicit, allowlisted **tool set**. A tool is the
connector from the brain to a body actuator (serve, pass, set, spike, block, dig). The
brain may only invoke the tools in its `tools` list — this is the permission boundary.

No database, shell, or network tools are ever granted. An action that is not in the
agent's tool list is rejected.

## Decision validation

Every LLM decision is validated against the tool list and clamped (power to `[0,1]`,
target to the court bounds, `move_to` to the player's own half) before it reaches the
core. Invalid output falls back to a deterministic default — never crashes, never mutates
state arbitrarily.

## Sensors (perception)

The brain may only read its **sensors** (ball, own half, own attributes, rally history,
score). It must never read the opponent's hidden attributes.

## Prompt injection

Student instructions, persona, and skills are data, not system instructions. The runtime
clearly separates platform/rules text from player-authored text.

## Match isolation

Each match has isolated state, isolated teams, and seeded RNG. A player can read/write
only their own team; opponent attributes are hidden until revealed by the game.

## Core files (authorization)

- Students (all levels) can **read** the core files (`rules.yaml`, `physics.yaml`,
  `referee.md`) but **not modify** them.
- Only `admin` users can edit the core files. Critical parameters show a caution legend,
  and the admin can always **restore defaults**.

## Strategy presets (authorization)

Strategy presets (Aggressive / Defensive / Neutral) are admin-managed data stored as JSON
in `AppSetting`. They are plain configuration (persona/goal/skills/tools/params), never
executed code; only `admin` users can create/edit them.

## User administration (authorization)

- Only `admin` users may create/edit/delete accounts and change roles.
- A user cannot delete their own account.
- Deleting a user who still owns teams/matches is blocked with a clear message.

## Secrets

LLM API keys and database credentials are never written into the database or rendered
blueprints. Store them in environment variables only.
