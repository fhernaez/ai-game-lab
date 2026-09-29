# Educational Model

## Goal

Teach how LLMs work through a single, deeply-simulated game (beach volleyball). A match
is the outcome of many small decisions by AI agents, each combining a **mind** (LLM) and
a **body** (athlete attributes).

The interface must always make visible:

1. **what each parameter does**, and
2. **how it changes the player's behavior** — both for athlete attributes and for LLM
   model parameters.

## The core mental model: mind vs body

- **The mind (LLM)** chooses *what* to do — serve to the deep corner, set to the net,
  spike hard, or place soft. Its behavior is shaped by model + model parameters.
- **The body (attributes)** determines *whether it works* — whether the spike clears the
  net, whether the dig stays in bounds, whether the player reaches the ball in time.

A student learns by changing one knob at a time and reading the interaction log to see
the causal chain: decision → execution → outcome.

## Concept progression

1. **The agent** — a team has two players; each is an LLM with a role.
2. **Athlete attributes** — what each of the 7 skills does (jump, speed, dig, set,
   aim, power control, spike power).
3. **LLM model parameters** — temperature, top-p, penalties, max tokens, system prompt.
4. **Point-buy economy** — budgets and trade-offs; specialization vs balance.
5. **The physics** — how serve/flight/defense convert decisions + attributes into
   outcomes (stochastic, but seeded and readable).
6. **The match** — sets, points, faults, court switch, best-of-3.
7. **The interaction log** — reading the full trace to understand *why* a point was won
   or lost.
8. **Experimentation** — compare models, parameters, and attribute allocations.

## Transparency — the interaction log

For every play, the UI allows the student to inspect:

- which player acted, and in what situation;
- the prompt sent to the LLM;
- the model and model parameters used;
- the raw response and the parsed decision (action, target, power);
- the athlete attributes used;
- the physics outcome (in bounds, out, net, dig success);
- tokens and duration.

During the match, the graphical simulation shows the players and ball moving; the
interaction log records the reasoning behind each movement.

Do not expose hidden chain-of-thought. Show concise decisions, structured inputs/outputs,
and observable events.
