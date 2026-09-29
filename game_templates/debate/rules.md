# Rules

1. Each round, every crew member speaks once, in order: trainee → researcher → speaker.
2. Each message is fed into the next member's prompt.
3. After the discussion, the trainee (the speaker) proposes the crew's argument.
4. The referee model returns a structured verdict (accepted, score, explanation).
5. The verdict's score is clamped to the scoring rules.
6. The game runs for the configured number of rounds.
