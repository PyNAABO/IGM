import os
import re
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

# Limits & Scheduling (Conservative - Anti-Ban Priority)
MAX_ACTIONS_PER_RUN = 10
SCHEDULE_INTERVAL_MIN_HOURS = 3
SCHEDULE_INTERVAL_MAX_HOURS = 6
PROCESSED_USER_EXPIRY_DAYS = 28

# Conservative daily limits to avoid bans
MAX_DAILY_ACTIONS = 28
MIN_DELAY_BETWEEN_ACTIONS = 30
MAX_DELAY_BETWEEN_ACTIONS = 60

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def parse_count(text):
    """Parse Instagram count text like '1,234', '1.5M', or '691 followers' to integer."""
    if not text:
        return 0
    text = text.strip()
    text = text.replace(",", "").upper()
    
    multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
    
    # Extract numeric part first (handle "691 followers" or "889 following")
    match = re.match(r"([\d.]+)", text)
    if match:
        numeric_text = match.group(1)
        try:
            value = float(numeric_text)
            # Check for suffix multipliers
            for suffix, mult in multipliers.items():
                if suffix in text:
                    value *= mult
                    break
            return int(value)
        except ValueError:
            return 0
    
    # Fallback: try direct conversion
    for suffix, mult in multipliers.items():
        if suffix in text:
            try:
                return int(float(text.replace(suffix, "")) * mult)
            except ValueError:
                return 0
    
    try:
        return int(text)
    except ValueError:
        return 0


def get_counts_from_page(page, username):
    """Extract follower and following counts from profile page."""
    try:
        page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
    except Exception:
        return None, None

    # Check if we're on login page
    if page.locator("input[name='username']").count() > 0:
        print("WARNING: Session invalid - redirected to login page.")
        print("Please re-import cookies using: python -m scripts.import_cookies")
        return None, None

    followers = 0
    following = 0

    try:
        # Wait for header to be visible
        page.wait_for_selector("header", timeout=5000)
        
        header_links = page.locator("header a").all()
        for link in header_links:
            text = link.text_content() or ""
            if "followers" in text.lower() and followers == 0:
                followers = parse_count(text)
            elif "following" in text.lower() and following == 0:
                following = parse_count(text)
    except Exception as e:
        print(f"Warning: Could not extract counts from header: {e}")

    # Fallback: try to extract from spans
    if followers == 0 or following == 0:
        try:
            header_spans = page.locator("header span").all()
            for span in header_spans:
                text = span.text_content() or ""
                if "followers" in text.lower() and followers == 0:
                    followers = parse_count(text)
                elif "following" in text.lower() and following == 0:
                    following = parse_count(text)
        except Exception:
            pass

    return followers, following


def calculate_actions_per_run(follower_count, following_count, feature_type):
    """
    Calculate safe actions per run based on account size.
    Conservative approach: Complete coverage in ~28 days without exceeding daily limits.
    """
    total_users = follower_count if feature_type == "follow" else following_count

    if total_users <= 0:
        return MAX_ACTIONS_PER_RUN

    # Estimate runs per day based on schedule interval
    avg_hours = (SCHEDULE_INTERVAL_MIN_HOURS + SCHEDULE_INTERVAL_MAX_HOURS) / 2
    runs_per_day = 24 / avg_hours

    # Calculate actions needed per day for full coverage in PROCESSED_USER_EXPIRY_DAYS
    actions_needed_per_day = total_users / PROCESSED_USER_EXPIRY_DAYS

    # Use conservative daily limit
    target_daily_actions = min(actions_needed_per_day, MAX_DAILY_ACTIONS)

    # Calculate actions per run
    actions_per_run = max(1, int(target_daily_actions / runs_per_day))

    # Cap at a safe maximum
    safe_max = min(15, MAX_DAILY_ACTIONS // 2)
    return min(actions_per_run, safe_max)
