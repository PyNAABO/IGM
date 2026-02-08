import redis
import json
import logging
import time
import random
from datetime import datetime, timedelta
from config import REDIS_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_redis_client():
    """Connects to Redis using the URL from config."""
    if not REDIS_URL:
        logger.warning("REDIS_URL not set. Session persistence disabled.")
        return None
    try:
        # Use decode_responses=True to get strings instead of bytes
        # Add timeouts to prevent hanging connections
        return redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,  # 5 seconds to connect
            socket_timeout=5,  # 5 seconds for socket operations
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def save_cookies(username, cookies):
    """Saves Playwright cookies to Redis."""
    r = get_redis_client()
    if not r:
        return False
    try:
        r.set(f"session:{username}", json.dumps(cookies))
        logger.info(f"Cookies saved for user: {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False


def load_cookies(username):
    """Loads Playwright cookies from Redis."""
    r = get_redis_client()
    if not r:
        return []
    try:
        data = r.get(f"session:{username}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
    return []


def check_schedule(username):
    """Checks if it's time to run based on Redis timestamp."""
    r = get_redis_client()
    if not r:
        # CRITICAL: Default to NOT run if Redis fails (safer behavior)
        # This prevents accidental rate-limit violations
        logger.warning(
            "Redis unavailable. Defaulting to SKIP run for safety. "
            "Fix your Redis connection to resume automation."
        )
        return False  # Changed from True - safer default

    next_run = r.get(f"schedule:{username}:next_run")
    if next_run:
        now = datetime.now().timestamp()
        if now < float(next_run):
            wait_hours = (float(next_run) - now) / 3600
            logger.info(f"Skipping run. Next run scheduled in {wait_hours:.2f} hours.")
            return False

    return True


def update_schedule(username):
    """Sets the next run time to a random interval (2-5 hours) - Balanced approach."""
    r = get_redis_client()
    if not r:
        return

    hours = random.uniform(2, 5)  # Balanced: 5-12 executions/day
    next_run = datetime.now() + timedelta(hours=hours)
    r.set(f"schedule:{username}:next_run", next_run.timestamp())
    logger.info(f"Next run scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
