# Prompt Architecture

The system composes prompts from controlled sections. The volleyball engine builds a
prompt each time a player must make a decision (serve, dig, set, spike, place, block).

## Prompt layers

```text
1. Platform Role (you are a beach-volleyball agent)
2. Game Rules (authoritative; score, set, win condition)
3. Your Role (which player you are, your athlete attributes)
4. Team Strategy (player-authored instructions)
5. Current Match State (ball, scores, sets, server, touches, possession)
6. Available Actions + target coordinate space
7. Output contract (return JSON decision)
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
Set 1, score 12-10, your team to serve, ball at (4.0, 0.0, 0.0).

AVAILABLE ACTIONS
SERVE, DIG, SET, SPIKE, PLACE, BLOCK. Target coordinates X in 0..8, Y in 0..16.

Return JSON: {"action": "...", "power": 0.0..1.0, "target": [x, y]}
```

## Important

- Do not put authoritative rules *only* in the prompt; the physics/rules modules validate
  independently.
- Student-authored text is clearly marked as player configuration and must not replace
  platform or rules text.

## Output protocol

```json
{"action": "SERVE", "power": 0.8, "target": [7.2, 0.4]}
```

If a model returns invalid output, the engine falls back to a deterministic default and
records the failure in the interaction log.
