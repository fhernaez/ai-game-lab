# Agent Architecture

This is the canonical description of how an AI beach-volleyball player is built. The
whole platform follows one idea:

> The **brain** decides what to do. The **body** does it. The **core** decides what
> happens next.

Everything the advanced student sees in the **Advanced view** is a file that describes
one of these three parts.

---

## 1. The three parts

```text
BRAIN (the LLM agent)
├── persona     who the player is
├── goal        what the player wants (win the point / set)
├── task        what the player is doing right now (serve, defend, attack)
├── skills      the playbook: what the player KNOWS
├── tools       the connectors: what the player CAN do
├── sensors     what the player can SEE
└── memory      a small short-term memory (this rally)

        tools ↓                sensors ↑
BODY (the player's physical body)
├── actuators   the moves: run, jump, serve, pass, set, spike, block, dig
└── parameters  7 skills (sliders 1–10), bought with the budget

             actuators execute moves
                   ↓
CORE / REFEREE (the world)
├── rules       boundaries, scoring, win condition, court switch
├── physics     flight, speed, error (deterministic, seeded random)
└── environment  court, ball, sets, touches (the game state)
```

- **Brain** is the LLM (a model chosen from the providers).
- **Body** is a small, deterministic piece of code.
- **Core** is the deterministic referee + physics. It is **not** an LLM.

---

## 2. Tools vs skills (the key distinction)

These are **two different things**, and teaching the difference is part of the learning.

| | Tool | Skill |
|---|---|---|
| Meaning | What the player **can** do | What the player **knows** |
| Kind | Code connector brain → body | Natural-language playbook |
| Example | `spike` (calls the body's spike actuator) | "When the opponent is deep, place a soft shot short" |
| Stored in | `tools.yaml` | `skills/*.md` |
| Shows | Permission / capability | Strategy / knowledge |

Together they explain a decision: the player **could** spike (tool), and **chose** to
spike short (skill).

### Tool definition

```yaml
- id: spike
  action: SPIKE
  actuator: spike
  params: [power, target]
  requires: [jumping_height, shoot_max_power, shoot_accuracy_power]
  what: "Hit the ball hard over the net."
  effect: "Fast attack; short flight time, but less control."
```

A tool:
- links an `action` (what the brain outputs) to an `actuator` (a body move);
- lists the parameters it needs;
- lists the body parameters it uses (`requires`) — this is also the **permission** the
  brain has.

### Skill definition

```markdown
# Skill: Deep defense

## What it is
Drop back early and read the hitter's shoulder.

## Effect
Lets you dig hard, deep attacks and turn them into controlled passes.
```

Skills are written by the advanced student and injected into the brain's prompt, so the
LLM "knows" the strategy.

---

## 3. The other brain pieces

- **Persona / system instructions** — who the player is (e.g. "a patient defender").
- **Goal** — the objective (win this point).
- **Task** — the current job (serve / defend / attack); this is the `action_hint` the
  engine sends.
- **Sensors** — what the brain may read: ball position and flight time, its own half,
  its own attributes, the rally history, and the score. It must **not** read the
  opponent's hidden attributes.
- **Memory** — a small short-term memory: the messages of the current rally. There is no
  long-term memory in this version.
- **Prompt** — assembled from the pieces above plus a **side-specific** court-coordinate
  guide (`x` 0..8 across, `y` 0..16 down, net at `y = 8`), so the model knows which half
  it defends, where its end line is, and returns in-bounds targets and legal movement.
- **Strategy** — a complete preset chosen in the team configuration: the brain (persona,
  goal, skills, tools, model parameters) plus a body attribute allocation per match
  difficulty (easy / medium / hard) that respects each difficulty's budget. Three
  defaults (Aggressive / Defensive / Neutral) are seeded and the admin can add more.

---

## 4. Auto-explainable: `what` + `effect`

Every editable or readable element carries **two** plain-language fields:

```text
what    — what this thing IS (a short definition)
effect  — what it CHANGES on the player or the game (cause → effect)
```

This rule applies to:

- the 7 body parameters,
- every tool,
- every skill,
- every actuator,
- every rule and physics knob in the core.

The simple GUI shows `what` under each control and `effect` as a hint. The advanced view
shows both next to every field.

---

## 5. The files (advanced view)

The advanced student edits their **own** agent files; the core files are read-only.

```text
My team (editable)
├── agent.md       persona · goal · task
├── skills/*.md    playbooks (one file per skill)
├── tools.yaml     brain → body connectors (+ permissions)
└── body.yaml      actuators + the 7 parameters

Core (read-only for students; admin-editable)
├── rules.yaml     boundaries, scoring, win condition
├── physics.yaml   flight / speed / error constants
└── referee.md     what the deterministic referee does
```

- YAML files are validated and reconciled back into the structured config.
- Markdown files are stored verbatim as authored text.
- The admin can edit the core files; critical parameters show a caution legend, and the
  admin can **restore defaults**.
