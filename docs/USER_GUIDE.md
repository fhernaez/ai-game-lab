# AI Game Lab — User Guide (Beach Volleyball)

This guide explains how to use AI Game Lab V3: creating matches, configuring your
2-player team, running the volleyball simulation, and reading the interaction log.

---

## 1. Overview

AI Game Lab is an educational, multi-user platform for learning how large language
models work, through a single game: **beach volleyball**. A match is played by two teams
of two AI players each. Each player is the combination of:

- a **mind** — an LLM (model + model parameters) that decides the tactics;
- a **body** — 7 athlete attributes (sliders 1–10) that determine whether the execution
  works.

You configure both, run the match, and read the interaction log to see how each decision
and each attribute shaped the result.

Main areas:

1. **Matchmaking** — create a match, invite an online player, accept, ready up.
2. **Team configuration** — set your two players' attributes, archetype, model, and
   model parameters.
3. **Match** — the live graphical simulation and the interaction log.
4. **History** — browse every match.

### Roles

| Role | Typical use |
| --- | --- |
| `admin` | Manages users and settings. |
| `teacher` | Browses match history; manages the class. |
| `student` | Configures teams and plays matches. |

---

## 2. Logging in

Enter your username and password. New students can register from the login page; teachers
and administrators are usually created by an administrator.

---

## 3. Matchmaking

Open **Matchmaking**.

### 3.1 Create a match

Choose a **difficulty** (Easy / Medium / Hard — this sets the point budget for building
your team) and click **Create**.

### 3.2 Invite a player

On the match page, pick an **online player** and click **Invite**. They can **Accept** or
**Decline**.

### 3.3 Ready up

After accepting, each player configures their team (section 4) and clicks **I'm ready**.
When both are ready, the match starts automatically.

---

## 4. Configuring your team

Click **Configure my team** on the match page.

### 4.1 Athlete attributes (1–10 sliders)

Each player has 7 skills; drag the sliders. Every skill shows a plain-language
description of how it changes behavior:

- **Vertical Leap** — block spikes and hit downhill over the block.
- **Sand Speed** — cover the court and chase down shots.
- **Dig & Serve Receive** — control hard serves/spikes on the first touch.
- **Set Precision** — accurate passes to your partner.
- **Sniper Vision** — aim soft shots at empty sand.
- **Power Control** — keep accuracy when hitting at full power.
- **Spike Power** — attack velocity; less reaction time for the opponent.

### 4.2 Point budget

Each slider point above 1 costs 1 point, from the difficulty budget (Easy 45, Medium 25,
Hard 12). All attributes default to 1 (free). If you exceed the budget, the app rejects
the save and tells you the cost.

### 4.3 Preset archetypes

For a quick start, pick an archetype (applied to both players):

- **The Tower** — big blocks and heavy spikes, slow on the ground.
- **The Defensive Ninja** — covers ground and sets perfectly.
- **The Sharp-Shooter** — finesse and placements over power.

### 4.4 LLM model & parameters

Each player selects an **LLM model** (from the providers configured in the environment)
and model parameters, each with a short explanation:

- **Temperature** — how varied/creative the decisions are.
- **Max tokens** — max length of the response.
- **Top-p** — narrows/expands the sampled vocabulary.
- **Frequency / presence penalty** — reduce repetition.
- **System prompt** — the strategy/persona given to the agent.

### 4.5 Advanced view (view agent files)

On the team page, the **View agent files** tab shows each player as the files that make
up an agent: `agent.md` (persona/goal/task), `skills/*.md` (the playbook), `tools.yaml`
(brain→body connectors), and `body.yaml` (actuators + the 7 parameters). These are
read-only here — you edit them through the structured form. The **Core files** section
shows the game's rules, physics, and referee (read-only for students).

### 4.6 Strategy preset (Aggressive / Defensive / Neutral)

The **Strategy preset** selector pre-fills both players with a ready-made game plan: the
*brains* (persona, goal, skills, tools, model parameters) **and** the *body* attribute
allocation for the match's difficulty (easy / medium / hard), each within that
difficulty's budget:

- **Aggressive** — hard serves and spikes, high risk, high reward.
- **Defensive** — dig everything, keep the ball alive, force the opponent's error.
- **Neutral** — balanced, all-round play.

Administrators can add more alternatives in **Settings → Strategy presets**.

---

## 5. The match

Open **Matchmaking → your match**, or **History → View**.

### 5.1 The graphical simulation

A 2.5D perspective court shows the four players and the ball: each shot is a **ball flight
with a real trajectory and flight time** (the ball is drawn larger when high, with a ground
shadow and motion trail), and players — drawn as **animated humanoid figures** — run, jump,
serve, dig, set, spike, and block as they move smoothly to each decision's destination.
Whoever reaches the ball first plays the next touch. Blocks, net touches, and faults are
shown as they happen. Each serve starts from behind the end line. A live scoreboard shows
sets and points, and a **"▶ Match running…"** indicator confirms the match is in progress.
The animation is a separate, replaceable module.

### 5.2 The interaction log

The sidebar records every event, so you can trace *why* a point was won or lost:

- **Decision** — each agent's natural-language **message** (what it said it would do) and
  its parsed decision (action, power, target), plus the model and model parameters used.
- **Trajectory** — the ball flight (start, landing, flight time, random offset applied).
- **Intercept** — which player reached the ball and when.
- **Point / Fault** — the scoring outcome (landed, out, net).

### 5.3 Controls

- **Stop** — cancel a running/queued match.
- **Cancel** — abandon a match that hasn't started.
- **Delete** — remove a match and its history.

---

## 6. History

Open **History** to browse every match (finished and otherwise). Open a match's **Log** to
see its full interaction log and final state. This is where teachers review class results.

---

## 7. Settings & users (admin)

- **Settings** — edit the model list per provider and the global default model.
- **Settings → Core files** — edit the rules and physics knobs (with a caution legend on
  critical parameters) and the referee description; restore defaults at any time.
- **Users** — create accounts, change roles, delete users.

---

## 8. Key concepts

| Concept | Meaning |
| --- | --- |
| **Team** | Two players, owned by one user. |
| **Player (agent)** | An LLM (mind) + 7 athlete attributes (body). |
| **Attribute** | A physical/technical skill (0.1–1.0) that drives the physics. |
| **Model** | An LLM, referenced `provider:model`. |
| **Decision** | A structured action `{action, power, target}` produced by the LLM. |
| **Court coordinates** | `x` 0..8 across the court, `y` 0..16 down the court, net at `y = 8`. |
| **Interaction log** | The full trace of every decision and outcome. |

---

## 9. Typical classroom flow

1. The **teacher** creates student accounts (**Users**).
2. Two **students** create/accept a match and configure their teams (section 4).
3. They ready up; the match runs; they watch the simulation and read the log (section 5).
4. The class compares results in **History**, discussing how attributes and model
   parameters changed the outcome.
