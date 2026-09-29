# Initial Game Templates

## Template 1 — AI Debate Challenge

### Concept

Two crews debate a proposition through dialogue.

Each crew has three members with a speak order:

1. **trainee** (speaker/proposer) — coordinates and proposes the team's argument
2. **researcher** — provides evidence and analysis
3. **speaker** — articulates the team's position

Each round:

```text
trainee speaks → researcher speaks → speaker speaks → trainee proposes the argument
→ referee verdict (score + explanation)
```

The referee (an LLM) evaluates: relevance, evidence use, response to the opposing
argument, clarity, adherence to rules.

### Educational concepts

- model parameters (temperature, top-p, penalties, max tokens)
- prompt / system-prompt design
- reading the interaction log
- research and argumentation skills
- team (crew) communication
- how the referee model scores

## Template 2 — AI Team Sports

### Concept

A generic turn-based team sport, played as dialogue between two crews.

Possible crew members:

- trainee (speaker/proposer)
- attacker
- defender
- specialist

Possible actions: `MOVE`, `PASS`, `DEFEND`, `ATTACK`, `SHOOT`, `SUPPORT`.

Each round the crew discusses (each member speaks in order), the trainee proposes an
action, and the referee returns a verdict with a score.

The template can be customized into different sports by changing rules, action set,
scoring, roles, and speak order.

### Educational concepts

- multi-agent (crew) coordination
- communication and planning
- resource allocation
- state, actions, feedback
- the referee model and its verdict guard

## Important

The templates are examples, not hard-coded game implementations. The runtime executes
their generic blueprint (roles + speak order + actions + scoring + referee).
