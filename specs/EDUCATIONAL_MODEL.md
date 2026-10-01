# Educational Model

## Goal

Teach how LLMs work by building a beach-volleyball team of AI agents. A player is a
**brain** (LLM) + **body** (moves and parameters) inside a **world** (rules + physics).

The interface must always answer two questions for every element:

1. **What is this?** (a short definition)
2. **What effect does it have?** (what it changes on the player or the game)

These two (`what` and `effect`) are shown together everywhere.

## The core mental model: brain vs body vs world

- **Brain** — decides *what* to do, using its **tools** (what it can do) and its
  **skills** (what it knows).
- **Body** — executes it with **actuators** (moves) and **parameters** (quality).
- **World / core** — applies the rules and physics, and scores.

## Concept progression

1. **The agent** — a team has two players; each is an LLM with a persona, goal, and task.
2. **Tools** — what the player *can* do (serve, pass, set, spike, block, dig). Tools are
   the connectors from the brain to the body.
3. **Skills** — what the player *knows* (the playbook: when and how to use its tools).
4. **Body parameters** — the 7 qualities (jump, speed, dig, set, aim, power control,
   spike power), each with a `what` and an `effect`.
5. **The world** — rules and physics (deterministic, seeded) that turn decisions into
   outcomes.
6. **Point-buy economy** — budgets and trade-offs; specialization vs balance.
7. **The interaction log** — reading the full trace (message, tool, skill, parameters,
   outcome) to understand *why* a point was won or lost.
8. **Advanced view** — edit the agent's files (persona, skills, tools, body) and read the
   core files.

**Strategies** are complete presets (Aggressive / Defensive / Neutral, admin-extensible)
that pre-fill a player's persona, goal, skills, tools, and model parameters, plus a body
attribute allocation per difficulty that fits that difficulty's budget — the tactical
counterpart to the body archetypes. The **humanoid player figures** in the simulation make
each movement (run, jump, serve, dig, set, spike, block) visually recognizable, helping
students connect a decision to the physical action.

## Transparency — the interaction log

For every play the student can inspect: which player acted, the message, the tool used,
the skill (if any), the parameters, the raw + parsed decision, and the physics outcome.
The graphical simulation shows the players and ball; the log shows the reasoning.

Do not expose hidden chain-of-thought. Show concise decisions and observable events.
