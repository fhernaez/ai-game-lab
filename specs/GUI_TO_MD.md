# GUI → Markdown/YAML Compiler

This is a central feature of the platform.

## Principle

The student edits structured GUI fields. The application generates the Markdown and
YAML representation.

```text
Student
  |
  v
Friendly GUI
  |
  v
Configuration DTO
  |
  v
Validation
  |
  v
Blueprint Compiler
  |
  +--> manifest.yaml
  +--> game.md
  +--> rules.md
  +--> scoring.md
  +--> referee.md
  +--> agents/*.md
  +--> skills/*.md
  +--> playground.yaml
  |
  v
Technical view (editable)
  |
  v
Parser
  |
  v
Validation
  |
  v
Configuration DTO (reconciled)
```

## Do not use Markdown as the database

The database stores structured configuration. Markdown/YAML is a generated/exported
representation. Technical-view edits are reconciled back into the structured store
through validation, so the structured configuration remains the single source of truth.

## Crew editor

The GUI should offer cards or tabs per **crew member**.

### Identity

- Name
- Role
- Description
- Speak order (where in the round it speaks)

### Objective

Plain-language text area.

### Model

- model (`provider:model`)
- temperature
- max tokens
- top-p
- frequency penalty
- presence penalty
- stop sequences
- response format (json/text)

Every field must show a plain-language explanation (e.g. "Temperature changes how varied
the responses can be"). This is the pedagogical core: students learn what each parameter
does by changing it and reading the resulting dialogue.

### Skills

Students select skills from the available skills. The GUI explains each skill.

### Behavior

Simple controls (cautious ↔ adventurous, independent ↔ collaborative, concise ↔
detailed) that map to structured parameters.

### Memory

- no memory
- short memory
- team memory
- long-term memory

### Communication

Visual permissions:

```text
Crew members        ✓
Referee             action only
Opponents           ✗
```

## Referee editor

The referee is configured like any crew member (model + parameters), plus its
structured-verdict format (fixed to JSON). The GUI should explain that the referee is an
LLM whose verdict is schema-validated and clamped by the rules.

## Game editor

Use a step-by-step wizard:

1. Game identity
2. Objective
3. Players and teams (1v1)
4. Crew roles and speak order
5. Speaker/proposer role
6. Rules
7. Actions
8. Scoring
9. Referee
10. Resources
11. Playground permissions
12. Test simulation
13. Publish/version

The student should always see a plain-language preview.

Example:

> Your game is a dialogue between two crews and a referee.
> Each crew has three members: trainee, researcher, speaker.
> Each round, every member speaks in order, the trainee proposes an action,
> and the referee returns a verdict with a score.
> The game runs for 6 rounds. The highest score wins.

The plain-language preview is the primary educational surface, but the raw
YAML/Markdown is always available via the Technical view rather than hidden.

## Interaction log

The execution view must render the **interaction log**: for every dialogue message,
show the role, the prompt sent, the parameters used, the raw response, and the parsed
result. This is the primary way students understand how the result was reached.

## Technical view

Every configuration screen offers a persistent **Technical view** toggle. It renders the
generated `manifest.yaml`, `playground.yaml`, blueprint JSON, and Markdown instruction
files live; edits are validated and reconciled back (Markdown stored verbatim), with
inline errors on failure.
