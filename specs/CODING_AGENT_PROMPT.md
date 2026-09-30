# Coding Agent Prompt — AI Game Lab V3 (Beach Volleyball)

You are the lead software engineer implementing **AI Game Lab V3**, an educational,
multi-user web application focused on a **single game: beach volleyball**.

Read every file in this specification before writing code — especially
`VOLLEYBALL_SPEC.md` and `AGENT_ARCHITECTURE.md`.

## Mission

Build a clean, maintainable, extensible Flask application where students:

1. log in and see who is online
2. create a match (choose difficulty) and invite another online player
3. accept/decline an invitation
4. configure their team of 2 players through a **simple GUI** (sliders, archetypes,
   model) **and an Advanced file view** (persona, skills, tools, body parameters)
5. mark ready; the match starts when both are ready
6. watch the graphical match simulation (players + ball on the court)
7. read the interaction log (message, tool, skill, parameters, outcome per play)
8. read (not modify) the core files; admins can edit them and restore defaults
9. browse match history; admins manage users and settings

## Non-negotiable architecture

- Flask is the web layer; the game logic lives in `app/domain/volleyball/`.
- Keep the **brain / body / core** separation (see `AGENT_ARCHITECTURE.md`):
  - `brain/` — the LLM agent (persona, goal, task, skills, tools, sensors, memory) and
    the decision protocol.
  - `body/` — the physical body (actuators, 7 parameters) — pure, deterministic code.
  - `core/` — the deterministic referee + world (rules, physics, environment). **Not an
    LLM.**
- PostgreSQL + Redis (queue + presence); SQLAlchemy + Alembic; Flask-Login.
- Jinja2 + HTMX + a small amount of JavaScript.
- Multi-provider / multi-model LLM abstraction; models selected from `LLM_PROVIDERS`.
- **The graphical simulation is an independent module** (`sim/`), driven
  only by the event stream.
- Store the full interaction log; persist events incrementally (commit each event).
- Run in its own venv; ship `requirements.txt`.

## Auto-explainable (`what` + `effect`)

Every parameter, tool, skill, actuator, rule and physics knob must carry two strings:
`what` (definition) and `effect` (what it changes on the player/game). The GUI shows both
in the simple and advanced views.

## Main navigation

1. **General Settings** (admin): providers, model lists, default model, and the core
   files (`rules.yaml`, `physics.yaml`, `referee.md`) with caution legend + restore.
2. **User Administration** (admin): list/create/role/delete users.
3. **Matchmaking**: create match, invite, accept, configure team, ready.
4. **Team configuration**: simple view (sliders/archetypes/model) + **Advanced file view**
   (`agent.md`, `skills/*.md`, `tools.yaml`, `body.yaml`).
5. **Match**: live simulation + interaction log; start/stop/delete.
6. **History**: browse finished matches.

## The engine

`engine.py` orchestrates the rally: the brain decides, the body executes, the core
resolves. Implement:

- `brain/tools.py` — a tool registry: `action → actuator` + required body params. This is
  also the permission list (an action not in the agent's tools is rejected).
- `brain/skills.py` — skills (playbook text) loaded and injected into the prompt.
- `brain/sensors.py` — the read-only perception view for the brain.
- `brain/memory.py` — short-term memory (the current rally messages).
- `body/actuators.py` — the move library; `body/parameters.py` — the 7 attributes + budget
  + archetypes + `what`/`effect`.
- `core/` — rules, physics (seeded), and environment state.

## Decision protocol

```json
{"message": "...", "action": "SERVE|DIG|SET|SPIKE|PLACE|BLOCK",
 "power": 0.0..1.0, "target": [x, y], "move_to": [x, y], "move_speed": 0.0..1.0}
```

Validate: action ∈ agent's tools → clamp power/target → clamp `move_to` to the player's
own half. On invalid output, fall back to a deterministic default.

## Testing requirements

Implement tests for: authentication+presence, user administration, team configuration
(sliders/budget/archetypes), the Advanced file view (render/save/round-trip), core-file
read-only + admin edit + restore defaults, brain tools permission check, skills injected
into the prompt, `what`/`effect` presence, volleyball rules + faults, physics
determinism, match lifecycle, interaction-log persistence, history.

## Implementation order

1. project skeleton (venv + requirements.txt)
2. configuration + database + migrations
3. authentication + presence + user administration
4. `body/` (parameters + actuators) with `what`/`effect`
5. `core/` (rules + physics + world)
6. `brain/` (agent, tools, skills, sensors, memory, decision)
7. engine
8. LLM abstraction
9. matchmaking + team configuration (simple view)
10. Advanced file view + core read-only/admin
11. match view + interaction log
12. graphical simulation (independent)
13. history
14. tests
15. Docker

## Code quality

Prefer simple explicit code. No microservices, no Kubernetes, no large frontend
framework. Pin dependencies. Document decisions in `docs/DECISIONS.md`.

## First milestone

> A user can log in, create a match, invite another user, both configure their 2 players
> (sliders + model), ready up, and watch one rally resolve (serve → touches → point) in
> the interaction log and the graphical simulation — and open the Advanced view to read
> the agent's files.
