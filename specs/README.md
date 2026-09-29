# AI Game Lab — V2 Architecture Specification

## Purpose

AI Game Lab is an educational, browser-based, multi-user platform for secondary-school
students to learn how large language models (LLMs) work, by pitting **crews of LLM
models** against each other in games.

The game is not a fixed simulation: **the game is the dialogue itself**. Two crews of
models, plus a **referee model**, converse in bounded rounds until a final result is
reached. Students learn by tuning each crew member's model and parameters and then
reading the interaction log to understand exactly how the result was reached.

The platform must expose the concepts that matter:

- a **crew** = a team of LLM agents, each with a role
- **dialogue** between crew members and the referee
- **roles, skills, tasks, prompts and instructions**
- **models and full model parameters** (temperature, top-p, penalties, max tokens, …)
- **memory, communication permissions, token budgets**
- **the referee model** and its structured verdicts
- **the interaction log** (the pedagogical trace: prompt, parameters, response)
- **event logs, replay, and a graphical interaction view**
- **multi-user matches**: invite another online player, each configures a crew, both
  ready up, then the game starts
- a **Technical view** (Markdown/YAML/JSON) for advanced students

## Core principle

**The game is a bounded dialogue between two crews of LLM models and a referee model.**

The final result emerges from that dialogue. The most important learning surface is the
ability to (1) configure every model parameter of every crew member, and (2) read the
interaction log to see how each decision was reached.

The GUI is the default authoring surface. An advanced student may always switch to the
**Technical view** to inspect and fine-tune the generated Markdown/YAML/JSON; edits are
validated and reconciled back into the structured configuration.

## V2 architecture

- Flask application
- Server-rendered HTML with Jinja2
- HTMX + a small amount of JavaScript for the graphical interaction view
- PostgreSQL for persistent data
- Redis for runtime queues / transient coordination (presence, async runs)
- SQLAlchemy + Alembic
- Flask-Login for accounts and session-based presence
- Multi-provider / multi-model LLM abstraction
- Generic **crew dialogue engine** (speak → act → referee)
- LLM referee with a schema/bounds guard
- Versioned Game Blueprints
- Event-based interaction log (prompt/parameters/response per message)
- Multi-user matchmaking (invite an online player, ready-up, auto-start)
- Two predefined game templates
- GUI-to-Markdown/YAML compiler + round-trip importer (Technical view)
- Graphical agent-interaction visualization during execution

## Initial predefined templates

1. AI Debate Challenge
2. AI Team Sports Challenge

The second template is intentionally generic enough to be customized into football,
rugby, tennis, volleyball, etc.

## Non-goals for V2

- Building a fully autonomous general-purpose agent framework
- Arbitrary Python execution by students
- Letting students modify referee/scoring logic during a competition
- Real-time physics simulation
- A complex visual game engine
- WebSocket/SSE push (presence and updates are polled; push may be added later)
- More than two players per match (V2 is 1v1)

The architecture must nevertheless allow these capabilities to be added later.

Editing the technical translation (Markdown/YAML/JSON) through the Technical view is not
arbitrary Python execution: it is constrained by the same validation that the compiler
applies, and Markdown is treated as inert instruction text.
