import redis
import os
from dotenv import load_dotenv

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

print(f"Testing Redis connection to: {REDIS_URL}")

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    # Ping
    print(f"Ping response: {r.ping()}")
    # Set/Get
    r.set("test_key", "test_value")
    val = r.get("test_key")
    print(f"Get response: {val}")
except Exception as e:
    print(f"Error: {e}")
