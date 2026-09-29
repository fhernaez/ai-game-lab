# Coding Agent Prompt — AI Game Lab V2

You are the lead software engineer implementing **AI Game Lab**, an educational,
multi-user web application for secondary-school students.

Read all files in this specification before writing code.

## Mission

Build a clean, maintainable, extensible Flask application that allows students to:

1. log in and see who is online
2. create a competition and invite another online player
3. accept/decline an invitation
4. configure their own crew (models + full parameters per member)
5. mark ready; the game starts when both players are ready
6. watch the dialogue (crew members speaking, the referee returning verdicts)
7. read the interaction log (prompt, parameters, response per message)
8. see referee verdicts and score evolution
9. inspect and replay a competition
10. inspect and edit the technical (Markdown/YAML/JSON) representation

The application must teach how LLMs work through experimentation.

## Non-negotiable architecture

- Flask is the web layer, not the game engine.
- Keep domain logic (dialogue, referee, guard) independent from Flask.
- Use application services between HTTP routes and domain logic.
- Use PostgreSQL and Redis (queue + presence).
- Use SQLAlchemy, Alembic, Flask-Login.
- Use Jinja2 + HTMX + a small amount of JavaScript.
- Implement a multi-provider / multi-model LLM abstraction.
- Do not hard-code a particular LLM vendor into the dialogue engine.
- Game definitions are versioned; competitions reference immutable game versions.
- Use structured configuration internally; generate Markdown/YAML artifacts.
- Provide a round-trip blueprint importer.
- **The game is a dialogue**: implement a generic `speak → act → referee` round loop.
- **The referee is an LLM** returning a structured verdict; apply a schema/bounds guard.
- **Store the full interaction log** (prompt, parameters, raw + parsed response, tokens)
  on every dialogue event.
- **Multi-user matches**: invite an online player, per-player crew ownership, ready-up.
- Do not use Markdown as the primary database.
- Do not allow student-authored Python execution or unrestricted agent tools.
- Run in its own venv; ship a `requirements.txt`.

## Educational UX

The app should feel like a laboratory. The two most important surfaces are:

1. **Crew configuration** — full model parameters per member, each with a plain-language
   explanation.
2. **The interaction log** — the readable trace of how the result was reached.

Use friendly labels. Advanced parameters may be grouped under an "Advanced" section.
A **Technical view** toggle must always be available.

## Main navigation

1. **General Settings** (admin): LLM providers (env-defined, read-only), editable model
   lists per provider, role defaults, global default model, resource limits. No secrets.
2. **Game Designer**: identity, objective, 1v1, crew roles + speak order, speaker role,
   rules, actions, scoring, referee, resources, playground permissions, test, version.
3. **Matchmaking**: create competition (game + round budget), invite an online player,
   accept/decline, configure your crew, ready-up.
4. **Competitions**: run/start, stop, delete; graphical dialogue view (default) and the
   interaction log / event timeline (alternate).
5. **Replay**: full event timeline, actions, verdicts, resource usage.

## Dialogue runtime

The runtime must support:

- two crews, each a set of crew members (roles with speak order)
- a speaker/proposer role per crew
- a referee model
- the `speak → act → referee` round loop
- a fixed `round_budget` (set per competition) and a wall-clock safety timeout
- structured actions and structured referee verdicts
- a deterministic verdict guard (schema + bounds)
- an event stream that drives the visualization and the interaction log

Use a clean state machine:

```text
CREATED → INVITED → ACCEPTED → CONFIGURING → READY → RUNNING → FINISHED/CANCELLED/DECLINED
```

## Prompt construction

Prompts are assembled from controlled sections:

1. platform instructions
2. game rules
3. role instructions
4. skills
5. crew instructions
6. player customization
7. current state
8. **prior dialogue messages this round** (each member sees what was said before it)
9. available actions
10. resource limits

Do not expose hidden chain-of-thought. Store the assembled prompt, parameters, and
response on every dialogue event.

## Referee

The referee is an LLM. It returns a structured verdict:

```json
{"accepted": true, "score": 3, "explanation": "..."}
```

A deterministic guard validates the schema, clamps the score, and only then applies the
state transition. Never let the referee mutate database state directly.

## Agent action protocol

Structured JSON objects, e.g.:

```json
{"action": "SUBMIT_ARGUMENT", "content": "..."}
```

Validate: schema → allowed action → role permission → current state → game rule. Then
apply the state transition.

## Testing requirements

Implement tests for:

- authentication + presence
- game creation + versioning
- blueprint compilation + invalid configuration
- crew/member configuration (parameters)
- matchmaking lifecycle (invite/accept/decline/ready)
- dialogue round loop (speak → act → referee)
- verdict guard (schema validation + score clamping)
- interaction log persistence (prompt/parameters/response)
- competition lifecycle (start/stop/delete)
- event persistence + replay
- resource accounting
- template loading

## Implementation order

1. project skeleton (venv + requirements.txt)
2. configuration
3. database + migrations
4. authentication + presence
5. game/version domain model
6. blueprint templates
7. GUI game editor (crew roles + speak order)
8. GUI crew/member editor (full parameters)
9. blueprint compiler + importer (round-trip)
10. LLM abstraction (multi-provider/multi-model)
11. dialogue runtime (speak → act → referee)
12. referee verdict guard
13. matchmaking (invite/accept/ready)
14. competition UI + controls
15. interaction log + visualization
16. events/replay
17. resource accounting
18. tests
19. Docker

At every stage keep the application runnable.

## Code quality

Prefer simple explicit code over clever abstractions. No microservices, no Kubernetes,
no large frontend framework. Pin dependencies in `requirements.txt`. Document important
decisions. When a requirement is ambiguous, prefer the simplest implementation and
record the assumption in `docs/DECISIONS.md`.

## First milestone

The first milestone is NOT a complete game. It is:

> A user can log in, create a competition, invite another online user, both configure
> their own crews (model + parameters per member) through a GUI, mark ready, and watch
> one round of the dialogue (each member speaks, the referee returns a verdict) appear
> in the interaction log.

Only after that workflow works should the full multi-round runtime be completed.
