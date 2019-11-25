import logging
import random

logger = logging.getLogger(__name__)


class RandomSelection:

    def __init__(self, possible_values, allow_multiple):
        self.possible_values = possible_values
        self.allow_multiple = allow_multiple

    def random_value(self):
        pass


class BasicRandomSelection(RandomSelection):

    def random_value(self):
        values_count = len(self.possible_values)
        if not values_count:
            return None
        if not self.allow_multiple:
            return random.choice(self.possible_values)
        random_picks = random.randint(1, values_count - 1)
        return random.sample(self.possible_values, random_picks)


def random_selection(possible_values, allow_multiple):
    return BasicRandomSelection(possible_values, allow_multiple).random_value()
