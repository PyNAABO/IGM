import os
from dotenv import load_dotenv

load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL")

# Timeouts (in milliseconds)
TIMEOUT_NAVIGATION = 60000
TIMEOUT_MODAL = 10000
TIMEOUT_ACTION = 5000
