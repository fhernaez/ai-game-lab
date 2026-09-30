"""Short-term memory: the messages of the current rally."""


class ShortTermMemory:
    def __init__(self, size=8):
        self.size = size
        self.messages = []

    def add(self, message):
        self.messages.append(message)
        if len(self.messages) > self.size:
            self.messages = self.messages[-self.size:]

    def render(self):
        return "\n".join(self.messages) or "(start of rally)"
