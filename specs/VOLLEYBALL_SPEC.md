# Beach Volleyball — Game Specification (V3)

This document is the authoritative, extremely detailed specification for the **single
game** implemented by AI Game Lab V3: a beach-volleyball simulation played by two teams
of AI agents.

The game is kept **generic-free**: the whole platform is optimized for this one sport.
The layered architecture (web → application → domain → infrastructure), the LLM
multi-provider abstraction, the multi-user matchmaking, and the interaction log are all
retained from V2 — but the "generic game designer" and the "crew dialogue of arbitrary
roles" are replaced by this single, deeply-simulated game.

---

## 1. Roles and team structure

- A **Team** is a pair of two **Players** (agents). There is **no trainee**.
- Each of the two users in a match owns one Team, and configures both of its Players.
- The two Players are interchangeable on the court (beach volleyball has no fixed
  positions), distinguished only by their attribute allocations.

Each **Player (agent)** carries two independent sets of configuration:

1. **Athlete attributes** — 7 numeric skills (section 4) that drive the physical
   simulation (how well the body executes).
2. **LLM configuration** — the model and model parameters (section 5) that drive the
   *decisions* (what the mind chooses to do).

This separation is the pedagogical heart of the app: the **mind** (LLM) decides the
tactics; the **body** (attributes) determines whether the execution succeeds.

---

## 2. Court and coordinate system

- **Court dimensions:** 16.0 m × 8.0 m total, split by a center net into two identical
  8.0 m × 8.0 m halves (`Court_A`, `Court_B`).
- **Ball** is a point vector `(X, Y, Z)`:
  - `X` = width, range `0..8` (side lines at 0 and 8).
  - `Y` = length, range `0..16` (end lines at 0 and 16; **net at Y = 8.0**).
  - `Z` = height, range `0..5` (net top at **2.43** m).
- Lines are **in bounds**.
- **"Own half" and "opponent's half" are side-relative.** A team defending the LEFT half
  owns `y 0..8` and attacks into `y 8..16`; a team defending the RIGHT half owns `y 8..16`
  and attacks into `y 0..8`. The prompt teaches this per side (see §5).

## 3. Match structure and rules

- **Teams:** exactly 2 teams (`Team_1`, `Team_2`), 2 players each, no substitutions.
- **Win condition:** best 2 of 3 sets.
  - Sets 1 & 2: first to **≥ 21 points** with a margin **≥ 2**.
  - Set 3 (tie-breaker): first to **≥ 15 points** with a margin **≥ 2**.
- **Court switch:** teams swap sides when the total combined points in the current set
  is `% 7 == 0` (sets 1 & 2) or `% 5 == 0` (set 3).
- **Possession:** a team has a maximum of **3 touches** to return the ball.
  - A **block** counts as touch #1.
  - The blocking player may make the immediate next contact (touch #2).
  - Consecutive touches by the same player are illegal **except after a block**.
- **Faults (ball goes to the opponent + point):**
  - **Net fault** — ball fails to clear the net (Z ≤ 2.43 at Y = 8.0) on a return.
  - **Out fault** — landing X or Y outside the opponent's boundaries.
  - **Illegal attack** — open-hand tip ("dink") over the net is a fault (modeled as a
    fault risk on the `PLACE` action); an open-hand set sent over the net is illegal.
  - **Net touch** — a player touching the net is a fault (risk grows with low jumping
    height near the net).
  - **4 touches** — a team touching the ball more than 3 times (guarded in the core).

All of the above are implemented by the deterministic core (`app/domain/volleyball/`).
A **block** is attempted when the incoming ball is a fast attack; a clean block scores a
point, a block touch counts as touch #1, and a block miss lets the ball continue.

---

## 4. Athlete attributes (physical/technical performance)

Every agent has 7 performance parameters valued from `0.0` (poor) to `1.0` (elite).
Internally they are stored as floats; in the UI they are **sliders 1–10** mapped by the
engine to `0.1 – 1.0` (`value = slider / 10`).

| # | UI label | Engine name | Meaning | Slider ends |
|---|----------|-------------|---------|-------------|
| 1 | Vertical Leap | `jumping_height` | Max Z reach for blocks and spikes. | 1 Floor Bound → 10 Airborne Elite |
| 2 | Sand Speed | `transition_speed` | How fast the player moves across the XY plane to intercept the ball. | 1 Sluggish → 10 Lightning Reflexes |
| 3 | Dig & Serve Receive | `receiving_accuracy` | Base multiplier for controlling an incoming serve/attack on first touch. | 1 Brittle Hands → 10 Impenetrable Wall |
| 4 | Set Precision | `passing_accuracy` | Accuracy when passing to the partner; diminishes linearly with partner distance. | 1 Erratic Passes → 10 Surgical Placements |
| 5 | Sniper Vision | `shoot_accuracy_distance` | Precision when aiming at empty sand on the far side (soft loop shots). | 1 Blind Hitting → 10 Laser Guided |
| 6 | Power Control | `shoot_accuracy_power` | Keeps precision when hitting at max power; low values = hard spikes fly out. | 1 Wild Swinger → 10 Controlled Chaos |
| 7 | Spike Power | `shoot_max_power` | Base attack velocity; higher velocity shrinks the opponent's reaction time. | 1 Soft Touches → 10 Cannon Arm |

### 4.1 The deterministic simulation core (trajectory + time)

On every hit, a deterministic core (seeded RNG — reproducible) performs these steps:

1. **Random component** — applies a normal-distribution offset to the target landing
   point, scaled by the relevant skill modifier and power (see §4.2).
2. **Trajectory + flight time** — computes the ball flight time
   `flight_time = distance / velocity`, where `velocity` grows with `shoot_max_power`.
   A harder hit is faster and gives the opponent less time.
3. **Movement / interception** — computes each defender's
   `reach_time = distance / (1.5 + 5.5·transition_speed)`. If a defender's `reach_time ≤
   flight_time`, that player reaches the ball before it lands and makes the next decision.
4. **Scoring** — if no defender reaches the ball, it lands and the core scores by its
   landing position (in bounds → point to the hitter; out/net → point to the opponent).

### 4.2 Trade-offs (behavior engine)

- **Power vs accuracy:** a max-power attack tests `shoot_accuracy_power`; a low value
  applies a large offset to the landing zone → high out probability.
- **Distance vs precision:** `passing_accuracy` / `shoot_accuracy_distance` increase the
  offset radius with distance and power.
- **Speed vs interception:** a high `transition_speed` shortens `reach_time`, letting the
  player cover more ground before the ball lands.

---

## 5. LLM model configuration (the "mind")

Each Player agent also selects an **LLM model** from the providers defined in the
environment (`LLM_PROVIDERS`), plus standard model parameters:

- `model` (`provider:model`)
- `temperature`
- `max_tokens`
- `top_p`
- `frequency_penalty`, `presence_penalty`
- `stop` (response format is always JSON, enforced by the prompt)

The LLM receives the current game state **plus the shared rally context** (the messages
every agent has produced so far this rally) and returns a **message + structured
decision** that covers **both** the ball hit and the player's own movement:

```json
{
  "message": "I spike hard to the open far corner",
  "action": "SERVE"|"DIG"|"SET"|"SPIKE"|"PLACE"|"BLOCK",
  "power": 0.0..1.0,
  "target": [x, y],
  "move_to": [x, y],
  "move_speed": 0.1..1.0
}
```

- `action` / `power` / `target` — the ball hit (technique, force, desired trajectory).
- `move_to` — the court position the player moves to (destination).
- `move_speed` — how fast the player sprints there (0.1 slow .. 1.0 elite).

The prompt sent to the LLM includes an explicit, **side-specific court-coordinate guide**
(see §2): `x` runs 0..8 across the court, `y` runs 0..16 down the court, and the net is
at `y = 8`. The guide tells the player which half it defends, where its end line is, and
that `target` must land in the opponent's half while `move_to` stays in its own half, so
models do not return out-of-range or own-half coordinates.

Every touch of a rally emits a ball trajectory — the **serve**, the **dig** (first touch),
the **set** (second touch), and the final **attack** — so the graphical simulation shows
the ball travelling continuously from one player to the next.

The **serve is taken from behind the end line** (outside the court); after serving, the
player moves inside to their `move_to`. The decision is then executed by the
deterministic core using the athlete attributes. The **interaction log** records, for
every decision: the message, the prompt, the model, the model parameters, the raw
response, the parsed decision (including movement), the athlete attributes, and the
physics outcome (trajectory, flight time, interception, fault).

### 5.1 Model parameter education

Every model parameter shown in the UI must carry a plain-language description of **how
it changes the agent's behavior**, e.g.:

- **Temperature** — how varied/creative the decisions are (low = predictable).
- **Max tokens** — how long the agent's reasoning/output can be.
- **Top-p** — narrows/expands the vocabulary sampled for a decision.
- **Frequency/presence penalties** — reduce repeated wording/ideas.
- **System prompt** — the persona/strategy the agent is given.

The user must be able to read, for each of their two agents, both the **athlete
attributes** and the **LLM parameters** with these explanations.

---

## 6. Point-buy economy and difficulty

The user distributes a **budget** across the 7 athlete attributes of their **two
agents**. Each slider point (1–10) costs **1 point**; every attribute defaults to **1**
(costing 0). Internal float scale: `0.1 – 1.0`.

| Difficulty | Budget | Average attribute level achievable |
|-----------|-------------|------------------------------------|
| EASY | 45 | ~7.4/10 — two elite all-rounders |
| MEDIUM | 25 | ~4.5/10 — specialized players |
| HARD | 12 | ~2.7/10 — mandatory flaws |

In V3, matches are **1v1 human-vs-human**: each of the two players receives the same
difficulty budget. (A single-player "vs AI" mode with an AI budget per difficulty is
reserved for a future version.)

### 6.1 Pre-set archetypes (quick setup, 25 points each — tuned for Medium)

- **THE TOWER (Net Dominator)** — big blocks and heavy spikes, slow on the ground.
  Allocates: Vertical Leap, Spike Power, Power Control, Sand Speed, Dig & Serve Receive.
- **THE DEFENSIVE NINJA (Floor Cleaner)** — covers ground, chases balls, perfect sets.
  Allocates: Sand Speed, Dig & Serve Receive, Set Precision, Sniper Vision.
- **THE SHARP-SHOOTER (Tactician)** — finesse over force, placements over power.
  Allocates: Sniper Vision, Set Precision, Dig & Serve Receive, Sand Speed.

### 6.2 Strategy presets (complete game plan, applies to both players)

The user picks a **strategy** that pre-fills the players' *brains* (persona, goal,
skills, tools, and model parameters) **and** a *body* attribute allocation per match
difficulty (easy / medium / hard) that stays within that difficulty's point-buy budget.
Three defaults are seeded, and the admin can create more:

- **Aggressive** — attack-first: hard serves and spikes, high risk. Persona "fearless
  attacker", goal "win fast with a hard attack", skills `smart_serve`/`placement_attack`,
  tools `serve, spike, place, block`, higher `temperature`; body favors jump and power
  at every budget.
- **Defensive** — defense-first: dig everything, force the error. Persona "patient
  defender", goal "keep the ball alive", skills `deep_defense`/`smart_serve`, tools
  `serve, dig, set, place`, lower `temperature`; body favors speed and receive at every
  budget.
- **Neutral** — balanced, all three skills and all six tools, default `temperature`;
  body balanced at every budget.

Strategies are stored in the `strategy_presets` AppSetting and managed by the admin.

---

## 7. Match flow (multiuser)

```
player A: create match (choose difficulty)                    status=created
          -> invite online player B                            status=invited
player B: accept                                               status=accepted
both:     configure team (2 players: sliders/archetype + model + params)
both:     ready                                                -> auto-start
          -> MatchEngine simulates sets/rallies                status=running
          -> finished                                          status=finished
```

The teacher (and any user) can browse **match history** (all finished matches stored in
the database with their full interaction log).

---

## 8. Graphical simulation (independent module)

The match view renders a **simple but accurate** animation of the four players and the
ball moving on the court. This is an **independent entity** — a self-contained module
(`app/web/static/js/sim/`) driven only by the event stream, so it can be
customized and enhanced later without affecting the rest of the app.

Requirements:

- Top-down or 2.5D court (16 × 8), net line, side/end lines.
- Four player markers (2 per team, distinct colors) that move smoothly to the position
  chosen in each `move_to` decision (constant size).
- A ball marker that animates along the trajectory using its flight time (with an arc for
  height) and is drawn **larger when high and smaller when low**.
- The serve starts **from behind the end line** (outside the court), then the server
  moves inside.
- A scoreboard (sets + current points) and a serve/possession indicator.
- A visible "running…" indicator while the worker is executing.
- The animation polls the event stream live (events are persisted incrementally by the
  worker) and is replayable from the stored event log.
- Players are drawn as **humanoid animated figures** (sprites stored in
  `app/web/static/img/players/`, one per movement — idle, run, serve, dig, set, spike,
  block, jump), with a procedural stick-figure fallback when no sprite is present.

---

## 9. Agent architecture & blueprint files

A player is an **embodied agent** (brain / body / core). The full model — persona, goal,
task, skills, tools, sensors, actuators, memory, and the `what`+`effect` explainability
rule — is defined in **`AGENT_ARCHITECTURE.md`**.

In the **Advanced view**, the advanced student edits these files for their own agents:

```text
agent.md      persona · goal · task
skills/*.md   playbooks
tools.yaml    brain → body connectors (and permissions)
body.yaml     actuators + the 7 parameters
```

and can read (but not modify) the core files:

```text
core/rules.yaml
core/physics.yaml
core/referee.md
```

The admin can edit the core files (with a caution legend on critical parameters and a
"restore defaults" action).
