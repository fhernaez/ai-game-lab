# Prompt Architecture

The system composes prompts from controlled sections. Within a round, prompts are built
incrementally: each crew member's prompt includes what earlier members already said.

## Prompt layers

```text
1. Platform Role
2. Game Rules
3. Crew-Member Role
4. Skills
5. Crew Instructions
6. Player Customization
7. Current State
8. Prior Dialogue This Round (messages from earlier members)
9. Available Actions
10. Resource Constraints
```

## Example conceptual prompt

```text
You are the RESEARCHER in an educational AI game.

GAME OBJECTIVE
...

YOUR ROLE
...

YOUR SKILLS
...

CREW INSTRUCTIONS
...

CURRENT GAME STATE
...

WHAT YOUR CREW HAS SAID SO FAR THIS ROUND
trainee: "Let's focus on the economic argument."
speaker: "Agreed, I need supporting evidence."

AVAILABLE ACTIONS
...

RESOURCE LIMITS
...

Produce one message that helps your crew.
```

## Important

Do not put the authoritative rules only in the LLM prompt. The prompt explains rules to
the agent; the runtime validates rules independently.

## Student instructions

Student-authored text must be clearly marked as player configuration. It must not be
allowed to replace platform or game-system instructions.

## Referee prompt

The referee receives:

- authoritative game rules
- current state
- the proposed action
- the round's dialogue (relevant history)
- scoring rules

The referee does not receive private information it should not have.

## Output protocol

Agents produce structured outputs validated against schemas.

Example crew message:

```json
{"message": "I found evidence supporting the economic argument."}
```

Example proposed action:

```json
{"action": "SUBMIT_ARGUMENT", "content": "..."}
```

Example referee verdict:

```json
{"accepted": true, "score": 3, "explanation": "Relevant and well supported."}
```

If a model produces invalid output, the runtime handles the error; it must not blindly
execute it.
