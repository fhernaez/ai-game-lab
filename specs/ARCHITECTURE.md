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
  +-- Game Designer
  +-- Matchmaking (invite / accept / ready-up)
  +-- Crew Configuration (per-player team settings)
  +-- Competition (run, start/stop/delete)
  +-- Interaction Log & Replay
  +-- Agent Interaction Visualizer
  |
  v
Application Services
  |
  +-- Blueprint Service
  +-- Agent Configuration Service
  +-- Prompt/Markdown Compiler
  +-- Blueprint Importer
  +-- Matchmaking Service
  +-- Presence Service
  +-- Dialogue Runner (competition execution)
  +-- Referee Service
  +-- Resource Service
  +-- LLM Service
  |
  v
Domain Layer
  |
  +-- Crew (team of LLM agents)
  +-- Crew Member (role + model + parameters)
  +-- Dialogue Loop (speak → act → referee)
  +-- Referee + Verdict Guard
  +-- Rule Engine
  +-- Action Engine
  +-- Score Engine
  +-- Event System (interaction log)
  |
  +------------------+
  |                  |
  v                  v
PostgreSQL          Redis
```

## 2. Architectural boundaries

### Web layer

Responsible for:

- HTTP requests, authentication, and session presence
- forms and the GUI
- graphical agent-interaction visualization (live and replay)
- matchmaking screens (invite, accept, ready-up)
- validation of user input

The web layer must not contain game rules or dialogue mechanics.

### Application layer

Responsible for workflows such as:

- create game from template
- save a game definition
- compile GUI configuration into blueprint files
- import/reconcile Technical view edits back into structured configuration
- manage multi-user matches (invite, accept, decline, ready)
- create a competition and its execution budget (rounds + wall-clock cap)
- run the dialogue loop
- persist the interaction log
- allocate resources

### Domain layer

Contains the generic game concepts:

- Game
- Crew
- CrewMember (role, model, parameters)
- DialogueRound
- Action
- Rule
- Score
- Referee
- Verdict (structured referee output)
- Competition
- Event

The domain layer must not depend on Flask.

### Infrastructure layer

Contains:

- PostgreSQL repositories
- Redis (queue + presence)
- LLM providers (multi-provider, multi-model)
- filesystem blueprint storage
- email service if later required

## 3. The game is a dialogue

A competition is a bounded dialogue between two **crews** and a **referee model**.

Each **round** has three phases:

```text
1. SPEAK    every crew member, in the role's speak order, produces one message
            (an LLM call). Each message is fed into the next member's prompt.
2. ACT      the team's speaker/proposer role proposes one structured action.
3. REFEREE  the referee model returns a structured verdict:
            {accepted, score, explanation}. The app validates and clamps it,
            then applies the state transition.
```

The loop repeats for a fixed number of rounds (set per competition), with a wall-clock
safety timeout. The final score is the result.

```text
for round in 1..round_budget:
    ROUND_STARTED
    for each team:
        for each crew member (in speak order):
            CREW_MESSAGE      # LLM call, logged with prompt + params + response
        ACTION_PROPOSED       # the speaker/proposer role proposes an action
        REFEREE_VERDICT       # referee model returns a structured verdict
        (verdict guard: validate schema, clamp score)
        SCORE_CHANGED / STATE_CHANGED
    ROUND_FINISHED
GAME_FINISHED
```

## 4. Crew and crew members

A **crew** is a team of LLM agents. Each **crew member** has:

- a **role** (defined by the game blueprint)
- a **speak order** (when it speaks within a round)
- a **model** reference (`provider:model`)
- **full model parameters** (see §5)
- **skills**, **instructions/system prompt**, **memory**, **communication permissions**
- a **resource budget** (tokens, time)

One role per crew is the **speaker/proposer** that submits the team's structured action
each round. All members speak before the action is proposed.

## 5. Crew-member model parameters

Every crew member exposes, and the app must allow configuring, at least:

- `model` (`provider:model`)
- `temperature`
- `max_tokens`
- `top_p`
- `frequency_penalty`
- `presence_penalty`
- `stop` (stop sequences)
- `system_prompt` / role instructions
- `response_format` (`json` / `text`)

The **referee is also a crew member** with its own parameters; its `response_format` is
always a structured verdict.

## 6. Referee and the verdict guard

The referee is a **real LLM model**, but it must return a structured verdict:

```json
{
  "accepted": true,
  "score": 3,
  "explanation": "The argument was relevant and well supported."
}
```

Before the verdict is applied, a deterministic **guard**:

1. validates the JSON schema;
2. checks `accepted` is boolean;
3. clamps `score` to the scoring rules (min/max, valid events);
4. attaches the referee's `explanation` to the log.

The referee may interpret ambiguity, but it can never corrupt state: its output is
always schema-validated and bounded. This is the same principle as the previous
"deterministic validation is authoritative", now with the referee as an LLM whose
output is fenced by deterministic checks.

## 7. The interaction log (event sourcing)

Every meaningful transition emits an immutable event. The **interaction log is the
primary learning surface**, so dialogue events carry the full trace:

For `CREW_MESSAGE` and `REFEREE_VERDICT` events, the payload includes:

- `role`, `round`, `actor`
- the **assembled prompt** actually sent
- the **parameters** used for that call
- the **raw model response**
- the **parsed structured result**
- `tokens_input`, `tokens_output`, `duration_ms`, `model`

Event types:

```text
GAME_CREATED
GAME_STARTED
ROUND_STARTED
CREW_MESSAGE
ACTION_PROPOSED
REFEREE_VERDICT
STATE_CHANGED
SCORE_CHANGED
ROUND_FINISHED
GAME_FINISHED
```

The current game state is stored for efficient access; events provide the log, replay,
and the visualization.

## 8. Multi-user matches

```text
player A: create competition (choose game + round budget)   status=created
          -> invite an online player B                        status=invited
player B: accept (or decline)                                 status=accepted (or declined)
both:     configure their own crew (models + parameters)      status=configuring
both:     mark "ready"                                        status=ready
          -> game auto-starts                                 status=running -> finished/cancelled
```

- **1v1**: two teams, one player owns each team.
- **Presence**: a user is "online" if authenticated with recent activity
  (`last_seen_at` within a short window). Polled periodically.
- **Authorization**: a player can read/write only their own team.
- **Invitations and ready state** are stored on the competition and polled; WebSocket
  push is out of scope.

## 9. Versioning

Every competition must reference an immutable game version.

Changing the game definition creates a new version. A historical competition must never
silently change because the game designer edited a template later.

## 10. Educational design principle

The GUI should expose concepts progressively, but the pedagogical core is:

1. **configure every model parameter** of every crew member, and
2. **read the interaction log** to trace how each decision was reached.

Beginner view: role, what it does, which model, temperature, how many tokens.

Advanced/teacher view: full parameter set (top-p, penalties, stop sequences, system
prompt, response format), memory limits, tool permissions.

The **Technical view** is always available as a toggle on every configuration screen.

## 11. Execution visualization

The default view during execution is a graphical diagram of the dialogue:

- crew members and the referee appear as nodes;
- messages, proposed actions, referee verdicts, and score changes appear as edges/annotations;
- the diagram animates as events stream in (polling), and is replayable from the log;
- the raw interaction log is an alternate view (not the default).

The visualization is driven entirely by the event stream; it must not require a
separate source of truth.
