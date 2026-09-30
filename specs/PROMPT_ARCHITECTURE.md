# Prompt Architecture

The system composes prompts from controlled sections. The volleyball engine builds a
prompt each time a player must make a decision (serve, dig, set, spike, place, block),
and injects the **shared rally context** — the messages every agent has already produced
this rally.

## Prompt layers

```text
1. Platform Role (you are a beach-volleyball agent)
2. Game Rules (authoritative; score, set, win condition)
3. Your Role (which player you are, your athlete attributes)
4. Team Strategy (player-authored instructions)
5. Current Match State (ball, flight time, scores, sets, server, touches)
6. Shared Rally Context (what every agent has said/done this rally)
7. Available Actions + target coordinate space
8. Output contract (return a message + JSON decision)
```

## Example conceptual prompt

```text
You are Player 1 on a beach-volleyball team.

GAME RULES
Best of 3 sets; sets 1-2 to 21, set 3 to 15, win by 2. Max 3 touches.

YOUR ATHLETE ATTRIBUTES (0.1-1.0)
jumping_height: 0.8, transition_speed: 0.6, receiving_accuracy: 0.7, ...

TEAM STRATEGY
Serve deep and attack the far corners.

CURRENT STATE
Set 1, score 12-10, your team to serve, ball at (4.0, 1.0, 0.0), flight time 1.1s.

WHAT HAS HAPPENED THIS RALLY
[Player A2] I serve with power to the far corner.
[Player B1] I dig and keep the ball alive.

AVAILABLE ACTIONS
SERVE, DIG, SET, SPIKE, PLACE, BLOCK. Target coordinates X in 0..8, Y in 0..16.

Return JSON: {"message": "...", "action": "...", "power": 0.0..1.0, "target": [x, y]}
```

## Important

- Do not put authoritative rules *only* in the prompt; the deterministic core validates
  independently.
- Student-authored text is clearly marked as player configuration and must not replace
  platform or rules text.
- The shared rally context is informational: it tells an agent what happened, but never
  grants it hidden information about the opponent beyond what the game reveals.

## Output protocol

```json
{"message": "I spike hard to the open far corner", "action": "SPIKE", "power": 0.9, "target": [7.2, 14.5]}
```

If a model returns invalid output (or the LLM call fails), the engine falls back to a
deterministic default decision and records the failure/error in the interaction log.
