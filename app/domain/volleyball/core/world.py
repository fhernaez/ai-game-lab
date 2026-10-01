"""The world / environment: court state and scoreboard."""


class CourtState:
    def __init__(self):
        self.ball = {"x": 4.0, "y": 8.0, "z": 0.0}
        self.flight_time = 0.0
        self.sets_won = [0, 0]
        self.set_points = [0, 0]
        self.current_set = 1
        self.server = 0
        self.touches = 0
        self.last_toucher = None
        self.set_history = []
        self.winner = None
        self.sides = [0, 1]  # sides[team_index] = which half that team defends

    def combined_points(self):
        return self.set_points[0] + self.set_points[1]

    def to_dict(self):
        return {
            "sets_won": self.sets_won,
            "set_points": self.set_points,
            "current_set": self.current_set,
            "server": self.server,
            "set_history": self.set_history,
            "winner": self.winner,
            "ball": self.ball,
            "flight_time": self.flight_time,
        }
