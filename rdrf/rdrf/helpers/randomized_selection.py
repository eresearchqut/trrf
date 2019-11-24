import logging
from random import randint

logger = logging.getLogger(__name__)


class RandomSelection:

    def __init__(self, possible_values, allow_multiple):
        self.possible_values = possible_values
        self.allow_multiple = allow_multiple

    def random_value(self):
        pass


class BasicRandomSelection(RandomSelection):

    def random_value(self):
        logger.info(f"Possible values: {self.possible_values}")
        values_count = len(self.possible_values)
        if not values_count:
            return None
        if not self.allow_multiple:
            random_index = randint(0, values_count - 1)
            logger.info(f"Random value: {self.possible_values[random_index]}")
            return self.possible_values[random_index]
        else:
            random_picks = randint(1, values_count - 1)
            results = []
            while len(results) < random_picks:
                random_index = randint(0, values_count - 1)
                if self.possible_values[random_index] not in results:
                    results.append(self.possible_values[random_index])
            logger.info(f"Random values: {results}")
            return results


def random_selection(possible_values, allow_multiple):
    return BasicRandomSelection(possible_values, allow_multiple).random_value()
