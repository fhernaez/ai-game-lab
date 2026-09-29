# AI Game Lab — V3 Specification (Beach Volleyball)

## Purpose

AI Game Lab is an educational, browser-based, multi-user platform for learning how large
language models work — by configuring **teams of AI agents** that play a **single,
deeply-simulated game: beach volleyball**.

V3 deliberately abandons the "generic game designer" in favor of **one game done well**.
The layered architecture, LLM multi-provider abstraction, multi-user matchmaking, and
interaction log are retained; the generic blueprint/dialogue system is replaced by a
beach-volleyball engine.

The pedagogical core is the separation between an agent's **mind** (the LLM: model +
parameters, deciding tactics) and its **body** (7 athlete attributes: how well the body
executes). Students configure both, run a match, and read the interaction log to
understand how each decision and each attribute shaped the result.

## What the platform exposes

- **Teams of 2 players** (no trainee), each player an AI agent.
- **7 athlete attributes** per player (Vertical Leap, Sand Speed, Dig & Serve Receive,
  Set Precision, Sniper Vision, Power Control, Spike Power), set with 1–10 sliders.
- **Point-buy economy** with difficulty levels (Easy/Medium/Hard) and preset archetypes.
- **LLM model + model parameters** per player, each with a plain-language explanation.
- **Models chosen from a list** built from the `LLM_PROVIDERS` environment variable.
- **Multi-user matches**: invite an online player, each configures their team, both ready
  up, the match auto-starts.
- **Interaction log**: prompt, model, parameters, raw + parsed decision, athlete
  attributes, and physics outcome for every play.
- **Graphical match simulation**: an independent, self-contained animation module of the
  players and ball on the court.
- **Match history**: every match persisted and browsable by teachers.

## V3 architecture

- Flask application, Jinja2 + HTMX + a small amount of JavaScript
- PostgreSQL for persistent data; Redis for the async queue + presence
- SQLAlchemy + Alembic; Flask-Login
- Multi-provider / multi-model LLM abstraction (`LLM_PROVIDERS` env)
- Beach-volleyball domain engine (state, rules, stochastic physics, attributes)
- Event-based interaction log
- Multi-user matchmaking (1v1)
- Independent graphical simulation module
- User administration (admin)

## See also

- `VOLLEYBALL_SPEC.md` — the complete game mechanics, attribute schema, and economy.
- `ARCHITECTURE.md`, `DATA_MODEL.md`, `EDUCATIONAL_MODEL.md`, `CODING_AGENT_PROMPT.md`,
  `SECURITY_AND_SANDBOX.md`, `FOLDER_STRUCTURE.md`, `PROMPT_ARCHITECTURE.md`,
  `DEFAULT_PROMPTS.md`.

## Non-goals

- A generic game designer for arbitrary games (removed in V3).
- Real-time physics rendering or 3D graphics (the animation is a simple 2D simulation).
- More than 2 teams, or more than 2 players per team.
- WebSocket push (presence and updates are polled; push may be added later).
