# Educational Model

## Goal

The application should teach how LLMs work through experimentation: configure every
model parameter of every crew member, run a dialogue, and read the interaction log to
understand how the result was reached.

The interface must make the relationship between configuration and model behavior
visible.

## Concept progression

### Level 1 — The crew member

Student learns:

- a crew is a team of LLM agents
- each member has a role and an objective
- each member uses a model

### Level 2 — Model parameters

Student learns what each parameter does by changing it and reading the dialogue:

- temperature
- max tokens
- top-p
- frequency/presence penalties
- stop sequences
- system prompt

The UI must never imply a "better" value — only different behavior.

### Level 3 — The dialogue

Student learns:

- members speak in order each round
- a message is fed into the next member's prompt
- one member proposes the team's action
- the referee returns a verdict

### Level 4 — Skills and instructions

Student learns:

- skills are reusable capabilities
- instructions (system prompt) steer behavior
- different members can have different skills

### Level 5 — Resources

Student learns:

- models have costs
- token budgets matter
- memory is limited
- computation is a resource

### Level 6 — The referee

Student learns:

- the referee is an LLM too
- its verdict is structured and clamped by the rules
- an LLM and deterministic rules can work together

### Level 7 — Experimentation

Student compares configurations:

- different models
- different parameters
- different prompts
- different skills
- different resource allocations

The platform should encourage experimentation rather than merely producing a winner.

### Level 8 — Technical translation

Advanced students read and fine-tune the generated blueprint (Markdown/YAML/JSON)
through the Technical view.

## Transparency — the interaction log

The most important surface is the **interaction log**. For every dialogue message, the
UI should allow students to inspect:

- who spoke (role, round)
- the full prompt that was sent
- the parameters used for that call
- the raw model response
- the parsed structured result
- tokens consumed and duration
- how the referee scored it

During execution, the UI shows the interaction graphically by default: messages, actions,
and referee verdicts appear as a visible causal chain that leads to the final result.

Do not expose hidden chain-of-thought. Show concise decision summaries, structured
inputs/outputs, and observable events instead.
