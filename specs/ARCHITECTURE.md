# Architecture

## 1. High-level model

```text
Browser
  |
  v
Flask Web Application
  |
  +-- Authentication & Presence
  +-- General Settings
  +-- User Administration
  +-- Matchmaking (invite / accept / ready-up)
  +-- Team Configuration (2 players: attributes + LLM model/params)
  +-- Match (live simulation, history, replay)
  +-- Interaction Log
  +-- Graphical Match Simulation (independent module)
  |
  v
Application Services
  |
  +-- Matchmaking Service
  +-- Presence Service
  +-- Team Service (attributes, point-buy, archetypes)
  +-- Match Service (create/start/run/stop/delete, history)
  +-- Settings Service (providers/models, defaults)
  +-- LLM Service
  |
  v
Domain Layer (beach volleyball)
  |
  +-- CourtState (ball, scores, sets, server, touches)
  +-- Rules (win condition, faults, possession, court switch)
  +-- Physics (stochastic serve/flight/defense)
  +-- Attributes (7 skills, point-buy, difficulty, archetypes)
  +-- MatchEngine (rally → point → set → match)
  +-- Decision protocol (LLM structured decisions)
  +-- Event System (interaction log)
  |
  +------------------+
  |                  |
  v                  v
PostgreSQL          Redis
```

## 2. Architectural boundaries

### Web layer

- HTTP, authentication, session presence, forms, GUI
- user administration
- team configuration screens (sliders, archetypes, model selection, parameter
  explanations)
- matchmaking screens
- match view + the graphical simulation (rendered client-side)
- validation of user input

No game rules or physics live in the web layer.

### Application layer

Workflows: create/invite/accept/ready matches, configure teams (validate budget),
run the match (enqueue to worker), persist the interaction log, expose history.

### Domain layer

The beach-volleyball engine (`app/domain/volleyball/`): court state, rules, stochastic
physics, athlete attributes, point-buy, difficulty, archetypes, and the match engine.
**No Flask imports.**

### Infrastructure layer

PostgreSQL, Redis (queue + presence), the LLM provider registry, and the filesystem.

## 3. The two halves of an agent

Every Player agent is the combination of:

1. **The mind** — an LLM (model + model parameters) that produces a structured
   decision each time it acts (serve target/power, dig, set, spike, place, block).
2. **The body** — 7 athlete attributes (0.1–1.0) that determine whether the execution
   succeeds, via the stochastic physics.

The interaction log records both halves for every play, so a student can see *why* a
point was won or lost.

## 4. The match engine

```
MatchEngine
  for each set (best of 3):
    while set not won:
      RALLY:
        SERVE      server's LLM -> message + {power, target}
                   core adds seeded random offset, computes flight time -> TRAJECTORY
        loop (until the ball lands):
          each defender moves; if reach_time <= flight_time:
            defender's LLM -> message + {action, power, target}
            core: new trajectory from the intercept point (offset + flight time)
            -> INTERCEPT + TRAJECTORY events
          else:
            ball lands -> core scores by position -> POINT
      set end -> SET_WON event
    court switch check (combined points % 7 == 0 or % 5 == 0)
  match end -> MATCH_FINISHED
```

The rally is **message-driven**: every agent's natural-language message and decision is
accumulated and shared to all later agents in the rally as context. The "core" is a
deterministic component (seeded RNG) that adds the random trajectory component, computes
flight time, simulates movement/interception, and scores — it is not an LLM.

All randomness is seeded per match so runs are reproducible and replayable.

## 5. Athlete attributes and point-buy

See `VOLLEYBALL_SPEC.md` for the full schema. The `attributes` domain module:

- maps slider 1–10 → float 0.1–1.0 (`value = slider / 10`);
- computes team cost from the budget (each slider point costs 1);
- enforces the difficulty budget;
- provides the three preset archetypes.

## 6. LLM providers and model selection

Providers (id, type, base_url, api_key) come from the `LLM_PROVIDERS` environment
variable; `mock` is always available offline. The **model list per provider** and the
**global default model** are admin-editable app settings. Team configuration renders the
model dropdown from these lists, with `provider:model` references.

## 7. Interaction log (event sourcing)

Every meaningful transition emits an immutable event with the full trace:

- `MATCH_STARTED`, `SET_STARTED`, `RALLY_STARTED`
- `DECISION` — the acting agent's message + LLM decision (prompt, model, model params,
  raw + parsed decision, athlete attributes, tokens, optional error)
- `TRAJECTORY` — the deterministic core's ball flight (`from_ball`, `ball`,
  `flight_time`, `offset`)
- `INTERCEPT` — which defender reached the ball and when
- `POINT` / `FAULT` — the scoring outcome
- `SET_WON`, `COURT_SWITCH`, `MATCH_FINISHED`

Events are **streamed and persisted incrementally** as the match runs (one commit per
event), so the live view updates in real time while the worker executes. If an event
cannot be persisted, the match is marked `failed` with the error — it must never run to
completion with an empty, silently-lost interaction log.

## 8. Multi-user matches

```
created → invited → accepted → (both ready) → running → finished/cancelled/declined
```

- 1v1: each user owns one Team of 2 players.
- Presence (`last_seen_at`) tracks who is online (polled).
- A match is enqueued **exactly once**: the start action is idempotent and refuses to
  re-enqueue a match that is already `queued` or `running`.
- A player can read/write only their own team.

## 9. Graphical simulation (independent)

`app/web/static/js/volleyball_court.js` is a **self-contained module** that renders the
court, the four players, and the ball, driven only by the event stream. It is designed
to be replaced/upgraded later without touching the rest of the app.

## 10. Educational design principle

The GUI must always answer: **what does this parameter do, and how will it change the
player's behavior?** Both athlete attributes and LLM model parameters carry
plain-language explanations. The interaction log is the primary learning surface.

## 11. Versioning

Every match references an immutable game definition (the V3 volleyball rules). Match
history must never change when the game rules are updated.
