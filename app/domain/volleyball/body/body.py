"""The player body: parameters + actuators + position."""

from . import actuators, parameters


class Body:
    def __init__(self, parameters_dict=None, actuators_list=None):
        self.parameters = parameters_dict or parameters.default_parameters()
        self.actuators = actuators_list or actuators.ACTUATOR_KEYS
        self.position = [4.0, 8.0]

    def can(self, actuator):
        return actuator in self.actuators

    def param(self, key):
        return self.parameters.get(key, 1)
