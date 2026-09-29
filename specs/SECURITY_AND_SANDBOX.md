# Security and Sandbox Rules

This is an educational multi-user application. Never execute arbitrary
student-generated Python.

## Student-generated content may include

- plain text (team/player instructions, system prompts)
- structured configuration (slider values, model references, model parameters)

## Student-generated content must not directly execute

- Python, shell commands, SQL, Docker commands, arbitrary HTTP requests, filesystem ops

## LLM tools

Agents are LLM decision-makers, not tool users. They return structured decisions only;
no database, shell, or network tools are granted.

## Decision validation

Every LLM decision is schema-validated and clamped (power to `[0,1]`, target to the
court bounds) before it reaches the physics engine. Invalid output falls back to a
deterministic default — never crashes, never mutates state arbitrarily.

## Prompt injection

Student instructions (system prompts, team strategy) are data, not system instructions.
The runtime clearly separates platform/rules text from player-authored text.

## Match isolation

Each match has isolated state, isolated teams, and seeded RNG. A player can read/write
only their own team; opponent attributes are hidden until revealed by the game.

## User administration (authorization)

- Only `admin` users may create/edit/delete accounts and change roles.
- A user cannot delete their own account.
- Deleting a user who still owns teams/matches is blocked with a clear message.

## Secrets

LLM API keys and database credentials are never written into the database or rendered
blueprints. Store them in environment variables only.
