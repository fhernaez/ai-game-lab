# Architecture

## 1. High-level model

```text
Browser
  |
  v
Flask Web Application
  |
  +-- Authentication & Presence
  +-- General Settings (admin)
  +-- User Administration (admin)
  +-- Matchmaking (invite / accept / ready-up)
  +-- Team Configuration (simple + Advanced file view)
  +-- Match (live simulation, history, interaction log)
  +-- Graphical Match Simulation (independent module)
  |
  v
Application Services
  |
  +-- Matchmaking / Presence / Team / Match / Settings services
  |
  v
Domain (beach volleyball) — see AGENT_ARCHITECTURE.md
  |
  +-- brain/   the LLM agent (persona, goal, task, skills, tools, sensors, memory)
  +-- body/    the physical body (actuators, 7 parameters)
  +-- core/    the deterministic world (rules, physics, environment)
  +-- engine   orchestrates brain -> body -> core, emits events
  |
  +------------------+
  |                  |
  v                  v
PostgreSQL          Redis
```

## 2. Architectural boundaries

### Web layer

HTTP, authentication, presence, forms, GUI, the Advanced file view, user administration,
and the graphical simulation (client-side). No game rules or physics here.

### Application layer

Workflows: create/invite/accept/ready matches, configure teams (validate budget),
run the match (enqueue to worker), persist the interaction log, expose history, and
manage settings (including the core files and the strategy presets the admin can edit).

### Domain layer (brain / body / core)

- **brain/** — the LLM agent: its persona/goal/task, its skills (playbook), its tools
  (brain→body connectors, also its permission list), its sensors (perception), and its
  short-term memory. Produces a **decision** (`{message, action, power, target,
  move_to, move_speed}`).
- **body/** — the physical body: a move library (actuators) and the 7 budget parameters.
  Executes the decision.
- **core/** — the deterministic referee + world: rules, physics (seeded), and environment
  state. Scores by the ball's landing position. **Not an LLM.**
- **engine.py** — the rally loop that wires the three together and emits the event stream.

### Infrastructure layer

PostgreSQL, Redis (queue + presence), the LLM provider registry, and the filesystem.

## 3. The interaction loop

```text
for each rally:
    SERVE:   brain(server) -> decision -> core resolves the serve trajectory
    until the ball lands:
        BODY:  a defender's body reaches the ball (or blocks)
        BRAIN: that player's brain -> decision (uses tools + skills)
        CORE:  resolves the touch / fault, updates the environment
    CORE:    scores by the ball's landing position
```

All randomness lives in the core and is seeded per match, so a run is reproducible.

## 4. Auto-explainable

Every parameter, tool, skill, actuator, rule and physics knob carries `what` (definition)
and `effect` (what it changes on the player/game). The GUI shows both; the Advanced view
shows them next to every field.

## 5. The interaction log (event sourcing)

Events: `MATCH_STARTED`, `SET_STARTED`, `RALLY_STARTED`, `DECISION` (message, prompt,
model, params, attributes, `skill_id`/`tool_id`), `TRAJECTORY`, `INTERCEPT`, `BLOCK`,
`POINT`, `SET_WON`, `COURT_SWITCH`, `MATCH_FINISHED`. Events are persisted incrementally
(one commit per event) so the live view updates in real time.

## 6. Multi-user matches

`created → invited → accepted → (both ready) → running → finished/cancelled/declined`.
1v1; each user owns one Team of two players. A match is enqueued exactly once.

## 7. Graphical simulation (independent)

`app/web/static/js/sim/` plays the event log sequentially: the ball flies
over its flight time (larger when high), players move smoothly to their `move_to`, and
the serve starts behind the end line. Players are humanoid animated figures (sprites in
`app/web/static/img/players/`, with a procedural stick-figure fallback). It is
self-contained and replaceable.
