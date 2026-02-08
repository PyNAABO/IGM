import logging
import sys
import json
import time
import redis
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from config import IG_USERNAME, IG_PASSWORD
from session_manager import load_cookies, save_cookies, check_schedule, update_schedule

# Configuration
MAX_ACTIONS_PER_RUN = 10
MIN_SLEEP = 10
MAX_SLEEP = 30

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def random_sleep():
    sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
    logger.info(f"Sleeping for {sleep_time:.2f}s...")
    time.sleep(sleep_time)


def process_unfollows(page):
    """Unfollows users who don't follow back."""
    logger.info("Checking 'Following' list for non-followers...")

    # Go to profile first
    page.goto(
        f"https://www.instagram.com/{IG_USERNAME}/", wait_until="domcontentloaded"
    )
    time.sleep(3)

    # Click "Following" link to open modal
    try:
        page.locator(f"a[href='/{IG_USERNAME}/following/']").click()
        page.wait_for_selector("div[role='dialog']", timeout=10000)
    except Exception as e:
        logger.warning(f"Could not open 'Following' dialog: {e}")
        return

    time.sleep(3)  # Wait for list to load

    # Extract visible usernames from the dialog
    # We target the links inside the dialog that look like user profiles
    links = page.locator("div[role='dialog'] div[role='button'] a").all()
    # If that selector fails, try generic 'a' in dialog
    if not links:
        links = page.locator("div[role='dialog'] a").all()

    usernames = []
    for link in links:
        href = link.get_attribute("href")
        if href and href.count("/") == 2:  # e.g. /username/
            user = href.strip("/")
            if user != IG_USERNAME:
                usernames.append(user)

    usernames = list(set(usernames))[:MAX_ACTIONS_PER_RUN]
    logger.info(f"Found {len(usernames)} users to check.")

    # Close dialog before processing (optional, but cleaner)
    # page.keyboard.press("Escape")
    # time.sleep(1)

    count = 0
    for user in usernames:
        if count >= MAX_ACTIONS_PER_RUN:
            break

        logger.info(f"Checking {user}...")
        try:
            page.goto(
                f"https://www.instagram.com/{user}/", wait_until="domcontentloaded"
            )
            time.sleep(random.uniform(3, 6))

            # Check for "Follows you" text
            follows_you = False
            if page.get_by_text("Follows you").count() > 0:
                follows_you = True

            if not follows_you:
                logger.info(f"{user} does NOT follow you. Unfollowing...")

                # Find the button that implies we follow them.
                # It usually says "Following"
                following_btn = (
                    page.locator("button").filter(has_text="Following").first
                )

                if following_btn.count() > 0:
                    following_btn.click()
                    time.sleep(2)
                    # Confirm Unfollow
                    page.get_by_role("button", name="Unfollow").click()
                    count += 1
                    random_sleep()
                else:
                    logger.warning(
                        "Could not find 'Following' button. Already unfollowed?"
                    )
            else:
                logger.info(f"{user} follows you. Keeping.")

        except Exception as e:
            logger.error(f"Error checking {user}: {e}")

    logger.info(f"Unfollowed {count} users.")


def process_followbacks(page):
    """Follows users back (Fans)."""
    logger.info("Checking 'Followers' list for fans...")

    # Go to profile first
    page.goto(
        f"https://www.instagram.com/{IG_USERNAME}/", wait_until="domcontentloaded"
    )
    time.sleep(3)

    # Click "Followers" link to open modal
    try:
        page.locator(f"a[href='/{IG_USERNAME}/followers/']").click()
        page.wait_for_selector("div[role='dialog']", timeout=10000)
    except Exception as e:
        logger.warning(f"Could not open 'Followers' dialog: {e}")
        return

    time.sleep(3)

    links = page.locator("div[role='dialog'] div[role='button'] a").all()
    if not links:
        links = page.locator("div[role='dialog'] a").all()

    usernames = []
    for link in links:
        href = link.get_attribute("href")
        if href and href.count("/") == 2:
            user = href.strip("/")
            if user != IG_USERNAME:
                usernames.append(user)

    usernames = list(set(usernames))[:MAX_ACTIONS_PER_RUN]
    logger.info(f"Found {len(usernames)} fans to check.")

    count = 0
    for user in usernames:
        if count >= MAX_ACTIONS_PER_RUN:
            break

        logger.info(f"Checking {user}...")
        try:
            page.goto(
                f"https://www.instagram.com/{user}/", wait_until="domcontentloaded"
            )
            time.sleep(random.uniform(3, 6))

            # Check for "Follow Back" or "Follow"
            # Logic: If they follow us, we usually see "Follow Back"
            # Or we see "Follow" AND "Follows you" text

            if page.get_by_text("Follows you").count() > 0:
                # They follow us. Check if we follow them.
                # If we followed them, button would be "Following".
                # If we don't, it's "Follow" or "Follow Back".

                if (
                    page.locator("button").filter(has_text="Follow").count() > 0
                    or page.locator("button").filter(has_text="Follow Back").count() > 0
                ):

                    # Exclude "Following" (contains "Follow" string sometimes, so check exact or specific)
                    if page.locator("button").filter(has_text="Following").count() == 0:
                        logger.info(f"User {user} follows you. Following back...")

                        # Click the first button that looks like a follow action
                        if page.get_by_role("button", name="Follow Back").count() > 0:
                            page.get_by_role("button", name="Follow Back").click()
                        else:
                            page.get_by_text("Follow").first.click()

                        count += 1
                        random_sleep()
            else:
                logger.info(f"{user} does not follow you. Skipping.")

        except Exception as e:
            logger.error(f"Error checking {user}: {e}")

    logger.info(f"Followed back {count} users.")


def main():
    if not IG_USERNAME or not IG_PASSWORD:
        logger.error("IG_USERNAME or IG_PASSWORD not set.")
        return

    # Check Schedule
    if not check_schedule(IG_USERNAME):
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        cookies = load_cookies(IG_USERNAME)
        if cookies:
            logger.info(f"Loading {len(cookies)} cookies from Redis.")
            context.add_cookies(cookies)
        else:
            logger.info("No cookies found in Redis. Starting fresh.")

        page = context.new_page()

        try:
            logger.info("Navigating to Instagram...")
            try:
                page.goto(
                    "https://www.instagram.com/",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
            except Exception as e:
                logger.warning(f"Navigation timeout: {e}")

            time.sleep(5)

            if page.locator("input[name='username']").is_visible():
                logger.error(
                    "Login form detected. Session invalid. Please run import_cookies.py."
                )
                return

            # Execute Features
            process_unfollows(page)
            # Short break between major tasks
            time.sleep(10)
            process_followbacks(page)

            # Update cookies and schedule
            new_cookies = context.cookies()
            save_cookies(IG_USERNAME, new_cookies)
            update_schedule(IG_USERNAME)

        except Exception as e:
            logger.error(f"Error during execution: {e}")
            page.screenshot(path="error.png")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
