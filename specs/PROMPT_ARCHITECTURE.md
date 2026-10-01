# Prompt Architecture

The brain's prompt is assembled from controlled sections. It tells the LLM *who* it is,
*what it can do* (tools), *what it knows* (skills), and *what it can see* (sensors).

## Prompt layers

```text
1.  Persona / system instructions     who the player is
2.  Goal                              win this point / set
3.  Task                              the current job (serve / defend / attack)
4.  Court coordinates                 the x/y/z axes, the net, and the target/move rules
5.  Skills                            the playbook (what the player knows)
6.  Tools                             what the player can do (and its permissions)
7.  Sensors                           what the player can see (game state, rally history)
8.  Memory                            the current rally messages (short-term)
9.  Output contract                   return a message + structured decision
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

COURT COORDINATES (meters) — side-relative
- x = across the court: 0 (left sideline) to 8 (right sideline).
- y = down the court: 0 to 16; the net is at y = 8 (2.43 m high).
- YOU defend the RIGHT half (y 8..16): your end line is y = 16.
- The OPPONENT's half is y 0..8 — aim every target there.
- target = where the ball lands (always in the OPPONENT's half).
- move_to = where you run (always in YOUR half).

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
- The coordinate guide is **side-specific**: the prompt tells each player which half it
  defends and which numeric range is the opponent's half, so the model does not aim into
  its own side.
- A chosen **strategy** pre-fills persona/goal/skills/tools/params before these sections
  are rendered.

## Output protocol

```json
{"message": "I spike hard to the open far corner", "action": "SPIKE", "power": 0.9,
 "target": [7.2, 14.5], "move_to": [4.0, 9.0], "move_speed": 0.8}
```

If the model returns invalid output, the engine falls back to a deterministic default and
records the failure in the interaction log.
