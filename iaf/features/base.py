import logging
import time
import random


class BaseFeature:
    def __init__(self, bot):
        self.bot = bot
        self.page = bot.page
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        """Execute the feature logic. Must be implemented by subclasses."""
        raise NotImplementedError

    def sleep(self, min_s=2, max_s=5):
        """Random sleep helper."""
        time.sleep(random.uniform(min_s, max_s))
