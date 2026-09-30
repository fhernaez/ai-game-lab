# Prompt Architecture

The brain's prompt is assembled from controlled sections. It tells the LLM *who* it is,
*what it can do* (tools), *what it knows* (skills), and *what it can see* (sensors).

## Prompt layers

```text
1.  Persona / system instructions     who the player is
2.  Goal                              win this point / set
3.  Task                              the current job (serve / defend / attack)
4.  Skills                            the playbook (what the player knows)
5.  Tools                             what the player can do (and its permissions)
6.  Sensors                           what the player can see (game state, rally history)
7.  Memory                            the current rally messages (short-term)
8.  Output contract                   return a message + structured decision
```

## Example conceptual prompt

```text
You are Player 1 on a beach-volleyball team.

PERSONA
A patient defender who reads the game.

GOAL
Keep the ball in play and set up the partner for a clean attack.

TASK
Defend and pass on the first touch.

SKILLS (what you know)
- Deep defense: drop back early and read the hitter's shoulder.

TOOLS (what you can do)
- serve, pass, set, spike, place, block, dig

SENSORS (what you can see)
- ball (x, y, z, flight time), your own half, your attributes, rally history, score

CURRENT STATE
Set 1, points 10-9, ball at (7.3, 7.3), flight time 0.74s.

WHAT HAS HAPPENED THIS RALLY
[Player 1] I serve deep to the corner.
[Player 2] I drop back to dig.

Return JSON: {"message": "...", "action": "...", "power": 0.0..1.0,
              "target": [x, y], "move_to": [x, y], "move_speed": 0.0..1.0}
```

## Important

- The **tools** are the permission list: an action not in the tools list is rejected.
- The **skills** are natural-language strategy; they guide reasoning but never grant new
  capabilities.
- Student-authored text (persona, skills) is clearly marked as player configuration and
  must not replace platform or rules text.
- Do not expose hidden chain-of-thought; the decision is a message + structured action.

## Output protocol

```json
{"message": "I spike hard to the open far corner", "action": "SPIKE", "power": 0.9,
 "target": [7.2, 14.5], "move_to": [4.0, 9.0], "move_speed": 0.8}
```

If the model returns invalid output, the engine falls back to a deterministic default and
records the failure in the interaction log.
