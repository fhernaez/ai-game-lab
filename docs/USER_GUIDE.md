# AI Game Lab — User Guide

This guide explains how teachers and students use AI Game Lab day to day: designing
games, configuring AI teams, running simulations, and reading the results.

---

## 1. Overview

AI Game Lab is an educational platform for learning AI concepts (agents, roles,
skills, prompts, models, memory, communication, resources, rules, and scoring) by
designing and playing games powered by teams of AI agents.

The three main areas are:

1. **Games** — the Game Designer, where a game is created and versioned.
2. **Playground** — where a student configures teams and agents, then runs a
   simulation.
3. **Competitions** — where a run is visualized and replayed.

### Roles

| Role | Typical use |
| --- | --- |
| `admin` | Manages settings and the environment; can do everything. |
| `teacher` | Designs games and manages the class. |
| `student` | Configures teams in the Playground and runs simulations. |

> Note: in the current V1 build every authenticated user can reach all screens;
> roles are stored on the account and reserved for finer access control.

---

## 2. Logging in

Open the application and enter your username and password. New students can create
their own account with **Register**; teachers and administrators are usually created
by an administrator (see the Startup Guide, section 5.3).

---

## 3. Games (Game Designer)

Open **Games** from the top navigation.

### 3.1 Create a game from a template

Click **New Ai Debate Challenge** or **New Ai Team Sports Challenge**. This copies a
seed template into your account as a new, editable game.

### 3.2 Design a game

Click **Design** on a game to edit it through a friendly form:

- **Game identity** — name, version, description.
- **Competition** — number of teams, turn mode, action timeout, duration (turns or
  rounds).
- **Teams & roles** — agents per team, and each role's count and whether it is
  required.
- **Resources** — team token budget, memory budget, max concurrent agents.
- **Referee** — enable or disable the referee agent.
- **Playground permissions** — which settings students may edit versus which are
  locked.
- **Instructions** — plain-language text for the game, rules, scoring, referee,
  each agent role, and each skill.

Click **Save version** to store your changes as a new immutable version.

### 3.3 View versions

The game's detail page lists every saved version. Competitions always reference the
version they were run against, so older results never change when you edit a game.

### 3.4 Technical view

Click **Technical view** to see the generated blueprint — `manifest.yaml`,
`playground.yaml`, and the Markdown instruction files — as editable text.

- Editing **YAML/JSON** and saving validates the changes and reconciles them back
  into the structured configuration (invalid edits are rejected with messages).
- Editing **Markdown** saves your text verbatim as the instruction content.

The Technical view is intended for advanced students and teachers who want to
understand or fine-tune the underlying architecture.

---

## 4. Playground

Open **Playground** from the top navigation.

### 4.1 Create a playground

Choose a game version and give the playground a name, then click **Create**. The
application automatically creates the required teams and agents from the game's
role definitions.

### 4.2 Configure teams and agents

On the playground's configuration page you can set:

- **Team instructions** and **strategy**.
- For each **agent**: its instructions, model, temperature, max tokens, and which
  skills are active.

Click **Save configuration** to keep your changes.

### 4.3 Run a simulation

Click **Run simulation**. The application creates a competition, queues it for the
background worker, and opens the graphical execution view. While the run is queued or
running, the view polls and animates events live; when it finishes, the final
scoreboard is shown.

---

## 5. Competitions

Open **Competitions** to list all runs.

### 5.1 Graphical execution view

This is the default view when a run opens. It animates how the agents interacted to
produce the result:

- **Agents and the referee** are drawn as nodes.
- **Messages**, **declared actions**, **accepted/rejected actions**, and **score
  changes** appear as animated edges and events.
- The **scoreboard** updates live and the **interaction log** records every event.

### 5.2 Event timeline (Replay)

Click **Event timeline** to see the raw, structured record of the run:

- **Final state** — the ending scores.
- **Actions** — every declared action with its request payload.
- **Events** — the full ordered event log.
- **Resource usage** — tokens consumed per agent.

---

## 6. Settings

Open **Settings** to see the environment summary: database connection, default LLM
provider and model, Redis status, the configured LLM providers and their models, and
the game templates directory. Secrets are never displayed.

### 6.1 Role defaults (admin)

Administrators see a **Role defaults** panel in Settings. It lists every AI role found
across the loaded games (trainee, researcher, speaker, attacker, …). For each role you
can choose a default **provider + model** (e.g. `ollama:llama3.2` or
`openai:gpt-4o-mini`), plus a global default model.

The default is used when an agent has no explicit model set in the Playground. The
resolution order for an agent's model is:

1. the agent's explicit model (set in the Playground),
2. the role default configured here,
3. the global default model,
4. the environment `DEFAULT_PROVIDER` / `DEFAULT_MODEL` fallback.

Click **Save role defaults** to persist changes. Providers themselves (endpoints and
API keys) are configured via the `LLM_PROVIDERS` environment variable, not here.

---

## 7. Key concepts

| Concept | What it means in the app |
| --- | --- |
| **Agent** | An AI role (trainee, researcher, speaker, attacker, …) with instructions, skills, a model, and a resource budget. |
| **Skill** | A reusable capability an agent can use (e.g. argumentation, spatial analysis). |
| **Prompt** | Assembled automatically from the game, role, skills, state, and allowed actions. |
| **Model** | The LLM behind an agent, referenced as `provider:model` (e.g. `ollama:llama3.2`, `openai:gpt-4o-mini`, or `mock:mock-model`). |
| **Memory** | What an agent is allowed to remember (short / team / long-term). |
| **Referee** | The agent that validates actions and applies scoring, constrained by deterministic rules. |
| **Blueprint** | The machine-readable game definition (YAML + Markdown) generated from your GUI edits. |
| **Event** | An immutable record of a game transition, used for the visualization and replay. |

---

## 8. Typical classroom flow

1. The **teacher** creates a game from a template and designs it (section 3).
2. The **teacher** sets up student accounts (Startup Guide, section 5.3).
3. Each **student** creates a Playground, configures their team and agents, and runs
   a simulation (section 4).
4. The class compares results in **Competitions**, using the graphical view and the
   event timeline to discuss why different configurations produced different outcomes
   (section 5).
