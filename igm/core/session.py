import redis
import json
import logging
import random
from datetime import datetime, timedelta
from .config import REDIS_URL, SCHEDULE_INTERVAL_MIN_HOURS, SCHEDULE_INTERVAL_MAX_HOURS

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_redis_client():
    """Connects to Redis using the URL from config."""
    if not REDIS_URL:
        # Warning already logged in main config or startup
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

    hours = random.uniform(SCHEDULE_INTERVAL_MIN_HOURS, SCHEDULE_INTERVAL_MAX_HOURS)
    next_run = datetime.now() + timedelta(hours=hours)
    r.set(f"schedule:{username}:next_run", next_run.timestamp())
    logger.info(f"Next run scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")


# User Tracking System - Prevents checking the same users repeatedly
PROCESSED_USER_EXPIRY_DAYS = 21  # 3 weeks


def mark_user_processed(username, target_user, feature_type):
    """
    Marks a target user as processed for a specific feature.

    Args:
        username: Bot account username
        target_user: Instagram username that was processed
        feature_type: 'follow' or 'unfollow'
    """
    r = get_redis_client()
    if not r:
        return False

    try:
        key = f"processed:{username}:{feature_type}"
        r.sadd(key, target_user)
        r.expire(key, PROCESSED_USER_EXPIRY_DAYS * 24 * 3600)
        return True
    except Exception as e:
        logger.error(f"Failed to mark user as processed: {e}")
        return False


def is_user_processed(username, target_user, feature_type):
    """
    Checks if a target user has already been processed.

    Args:
        username: Bot account username
        target_user: Instagram username to check
        feature_type: 'follow' or 'unfollow'

    Returns:
        bool: True if user was already processed, False otherwise
    """
    r = get_redis_client()
    if not r:
        return False

    try:
        key = f"processed:{username}:{feature_type}"
        return r.sismember(key, target_user)
    except Exception as e:
        logger.error(f"Failed to check if user was processed: {e}")
        return False


def filter_unprocessed_users(username, user_list, feature_type):
    """
    Filters out users that have already been processed.

    Args:
        username: Bot account username
        user_list: List of Instagram usernames to filter
        feature_type: 'follow' or 'unfollow'

    Returns:
        list: Filtered list containing only unprocessed users
    """
    r = get_redis_client()
    if not r:
        logger.warning("Redis unavailable, returning unfiltered list.")
        return user_list

    try:
        key = f"processed:{username}:{feature_type}"
        unprocessed = [u for u in user_list if not r.sismember(key, u)]

        processed_count = len(user_list) - len(unprocessed)
        if processed_count > 0:
            logger.info(
                f"Filtered out {processed_count} already-processed users. "
                f"{len(unprocessed)} remaining."
            )

        return unprocessed
    except Exception as e:
        logger.error(f"Failed to filter users: {e}")
        return user_list
