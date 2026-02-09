import os
from dotenv import load_dotenv

load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME")
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    print(
        "WARNING: REDIS_URL is not set. Session persistence and scheduling will be disabled."
    )

if not IG_USERNAME:
    raise ValueError("IG_USERNAME must be set in .env file.")

# Timeouts (in milliseconds)
TIMEOUT_NAVIGATION = 60000
TIMEOUT_MODAL = 10000
TIMEOUT_ACTION = 5000

# Limits & Scheduling
MAX_ACTIONS_PER_RUN = 10
SCHEDULE_INTERVAL_MIN_HOURS = 2
SCHEDULE_INTERVAL_MAX_HOURS = 5

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
