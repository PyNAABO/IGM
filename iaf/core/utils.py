import logging
import random
import time

# Configuration limits for random sleep
MIN_SLEEP = 10
MAX_SLEEP = 30

logger = logging.getLogger(__name__)


def random_sleep(min_s=MIN_SLEEP, max_s=MAX_SLEEP):
    """Sleeps for a random duration between min_s and max_s."""
    sleep_time = random.uniform(min_s, max_s)
    logger.info(f"Taking a human-like break for {sleep_time:.2f}s...")
    time.sleep(sleep_time)
