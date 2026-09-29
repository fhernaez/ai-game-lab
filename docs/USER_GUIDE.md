# AI Game Lab — User Guide

This guide explains how teachers and students use AI Game Lab day to day: designing
games, configuring crews, running multi-player matches, and reading the interaction log.

---

## 1. Overview

AI Game Lab is an educational, multi-user platform for learning how large language
models work. A match is a **dialogue between two crews of LLM models and a referee
model**: each round, crew members speak in order, one member proposes an action, and the
referee returns a verdict with a score.

The main areas are:

1. **Games** — the Game Designer, where a game's roles, actions, and scoring are defined
   and versioned.
2. **Matchmaking** — create a competition, invite an online player, accept, and ready up.
3. **Competitions** — the live match: configure your crew, watch the dialogue, and read
   the interaction log.

### Roles

| Role | Typical use |
| --- | --- |
| `admin` | Manages settings and the environment; can do everything. |
| `teacher` | Designs games and manages the class. |
| `student` | Configures crews and plays matches. |

> Note: in the current build every authenticated user can reach all screens; roles are
> stored on the account and reserved for finer access control.

---

## 2. Logging in

Open the application and enter your username and password. New students can register
from the login page; teachers and administrators are usually created by an administrator
(see the Startup Guide).

---

## 3. Games (Game Designer)

Open **Games** from the top navigation.

### 3.1 Create a game from a template

Click **New Ai Debate Challenge** or **New Ai Team Sports Challenge**.

### 3.2 Design a game

Click **Design** on a game to edit it:

- **Game identity** — name, version, description.
- **Execution budget** — default number of rounds and a wall-clock timeout.
- **Crew roles** — each role's speak order, which role is the **speaker** (proposes the
  action), and whether it is required.
- **Resources** — token/memory budgets, max concurrent agents.
- **Referee** — enable/disable.
- **Crew permissions** — which settings players may edit versus which are locked.
- **Instructions** — plain-language text for the game, rules, scoring, referee, each
  crew role, and each skill.

Click **Save version** to store your changes as a new immutable version.

### 3.3 View versions

The game's detail page lists every version. Competitions reference the version they were
run against, so older results never change when you edit a game.

### 3.4 Technical view

Click **Technical view** to see the generated blueprint — `manifest.yaml`,
`playground.yaml`, and the Markdown instruction files — as editable text. Editing
YAML/JSON validates and reconciles back into the structured configuration; Markdown is
stored verbatim.

---

## 4. Matchmaking

Open **Matchmaking**.

### 4.1 Create a competition

Choose a game version and a number of rounds, then click **Create**.

### 4.2 Invite a player

On the competition page, choose an **online player** and click **Invite**. The invited
player sees the invitation and can **Accept** or **Decline**.

### 4.3 Ready up

After accepting, each player configures their own crew (section 5) and clicks
**I'm ready**. When both players are ready, the game starts automatically.

---

## 5. Configuring your crew

On the competition page, click **Configure my crew**. For each crew member you can set:

- **Model** (`provider:model`, or inherit the role default)
- **System prompt / instructions**
- **Temperature**, **max tokens**, **top-p**
- **Frequency penalty**, **presence penalty**
- **Stop sequences**, **response format**

Plus the whole crew's instructions and strategy. Click **Save crew**.

This is the core of the learning: change a parameter, run the match, and read the
dialogue to see how it changed the outcome.

---

## 6. Competitions

Open **Competitions** to list your matches.

### 6.1 The graphical view

The default view is a node/edge diagram: crew members and the referee are nodes;
messages, proposed actions, and referee verdicts are animated edges; the scoreboard
updates live while the match runs (queued/running), then shows the final score.

### 6.2 The interaction log

The sidebar shows every event. For each dialogue message you can inspect:

- the role and round,
- the prompt sent,
- the parameters used,
- the raw response and the parsed result,
- tokens and duration.

This is how you trace *how* the result was reached.

### 6.3 Event timeline (Replay)

Click **Event timeline** for the raw structured record: final state, every action, the
full ordered event log, and resource usage.

### 6.4 Controls

- **Stop** — cancel a queued/running match.
- **Cancel** — abandon a match that hasn't started.
- **Delete** — remove a match and its history (cascade).

---

## 7. Settings

Open **Settings** to see the environment summary and, for administrators:

- **Models per provider** — edit the model list for each provider (providers themselves
  are env-defined in `LLM_PROVIDERS`).
- **Role defaults** — the default provider + model for each crew role.
- **Global default model**.

## 8. User administration (admin)

Open **Users** (visible only to administrators) to manage accounts:

- **Create user** — enter a username, email, role (`student` / `teacher` / `admin`), and
  password.
- **Change role** — select a new role and save.
- **Delete** — remove a user (blocked if they still own games, crews, or matches).

This is how you create the accounts needed to run a multi-player match: create two
students, log each one in, and invite one from the other in **Matchmaking**.

---

## 9. Key concepts

| Concept | What it means in the app |
| --- | --- |
| **Crew** | A team of LLM agents, owned by one player. |
| **Crew member** | An agent with a role, speak order, model, and parameters. |
| **Dialogue** | The `speak → act → referee` rounds that make up the game. |
| **Speaker** | The role that proposes the crew's action each round. |
| **Referee** | An LLM model returning a structured verdict, fenced by a guard. |
| **Model** | An LLM, referenced as `provider:model` (e.g. `ollama:llama3.2`). |
| **Interaction log** | The full trace (prompt, parameters, response) of every message. |
| **Event** | An immutable record of a game transition, used for the view and replay. |

---

## 10. Typical classroom flow

1. The **teacher** creates a game from a template and designs it (section 3).
2. The **teacher** sets up student accounts (Startup Guide).
3. Two **students** create/accept a match, each configure their crew (section 5), and
   ready up (section 4).
4. The class compares results in **Competitions**, reading the interaction log to
   discuss why different parameters produced different outcomes (section 6).
