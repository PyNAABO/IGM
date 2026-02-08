import logging
import sys
import time
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
    # Using more specific selector to avoid false matches
    links = page.locator("div[role='dialog'] a[role='link'][href^='/']").all()
    # Fallback: try with slightly less specific selector
    if not links:
        links = page.locator("div[role='dialog'] a[href^='/']").all()

    usernames = []
    for link in links:
        href = link.get_attribute("href")
        if href and href.count("/") == 2:  # e.g. /username/
            user = href.strip("/")
            if user != IG_USERNAME:
                usernames.append(user)

    all_usernames = list(set(usernames))
    usernames = all_usernames[:MAX_ACTIONS_PER_RUN]

    if len(all_usernames) > MAX_ACTIONS_PER_RUN:
        logger.info(
            f"Found {len(all_usernames)} users, limiting to {len(usernames)} for this run."
        )
    else:
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

            # CRITICAL: Check for "Follow Back" button first
            # If button says "Follow Back", it means they ARE following us!
            follows_you = False

            # Check for "Follow Back" button (appears when they follow you)
            follow_back_btn = page.locator("button").filter(has_text="Follow Back")
            if follow_back_btn.count() > 0:
                follows_you = True
                logger.info(f"'Follow Back' button found for {user}. They follow you!")

            # Also check for "Follows you" badge as secondary indicator
            elif page.get_by_text("Follows you").count() > 0:
                follows_you = True
                logger.info(f"'Follows you' badge found for {user}.")

            # If neither found, perform deep check in their following list
            else:
                logger.info(
                    f"No 'Follow Back' button or badge for {user}. Performing deep check in their Following list..."
                )
                try:
                    # Click "following" link (href containing /following/)
                    following_link = page.locator(f"a[href*='/{user}/following/']")
                    if following_link.count() > 0:
                        following_link.click()
                        time.sleep(random.uniform(2, 4))

                        # Wait for dialog and search input
                        search_input = page.locator(
                            "div[role='dialog'] input[placeholder='Search']"
                        )

                        if search_input.count() > 0:
                            search_input.fill(IG_USERNAME)
                            time.sleep(random.uniform(2, 4))

                            # Check if our profile appears in the results
                            my_profile_link = page.locator(
                                f"div[role='dialog'] a[href='/{IG_USERNAME}/']"
                            )

                            if my_profile_link.count() > 0:
                                follows_you = True
                                logger.info(
                                    f"Found {IG_USERNAME} in {user}'s following list. They follow you."
                                )
                            else:
                                logger.info(
                                    f"{IG_USERNAME} NOT found in {user}'s following list."
                                )
                        else:
                            logger.warning(
                                "Could not find search input in Following dialog."
                            )

                        # Close dialog
                        page.keyboard.press("Escape")
                        time.sleep(1)
                    else:
                        logger.warning(f"Could not find 'following' link for {user}")

                except Exception as e:
                    logger.warning(f"Deep check failed for {user}: {e}")
                    # If deep check fails, assume they DON'T follow to be safe
                    # This prevents accidentally keeping non-followers

            if not follows_you:
                logger.info(f"{user} does NOT follow you. Unfollowing...")

                # Find the button that implies we follow them.
                # It usually says "Following"
                following_btn = (
                    page.locator("button").filter(has_text="Following").first
                )

                if following_btn.count() > 0:
                    following_btn.click()
                    time.sleep(random.uniform(1, 2))

                    # Wait for confirmation modal to appear
                    try:
                        unfollow_confirm = page.get_by_role("button", name="Unfollow")
                        # Wait up to 5 seconds for the modal
                        unfollow_confirm.wait_for(state="visible", timeout=5000)
                        unfollow_confirm.click()
                        count += 1
                        logger.info(f"Successfully unfollowed {user}")
                        random_sleep()
                    except Exception as e:
                        logger.warning(f"Failed to confirm unfollow for {user}: {e}")
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

    # Using more specific selector to avoid false matches
    links = page.locator("div[role='dialog'] a[role='link'][href^='/']").all()
    if not links:
        links = page.locator("div[role='dialog'] a[href^='/']").all()

    usernames = []
    for link in links:
        href = link.get_attribute("href")
        if href and href.count("/") == 2:
            user = href.strip("/")
            if user != IG_USERNAME:
                usernames.append(user)

    all_usernames = list(set(usernames))
    usernames = all_usernames[:MAX_ACTIONS_PER_RUN]

    if len(all_usernames) > MAX_ACTIONS_PER_RUN:
        logger.info(
            f"Found {len(all_usernames)} fans, limiting to {len(usernames)} for this run."
        )
    else:
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

            # Critical: Validate session before any actions
            if page.locator("input[name='username']").count() > 0:
                logger.error(
                    "CRITICAL: Login form detected. Session invalid or expired."
                )
                logger.error("Please run: python import_cookies.py")
                page.screenshot(
                    path=f"error_session_invalid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                browser.close()
                sys.exit(1)  # Exit immediately to prevent triggering anti-bot

            # Execute Features
            process_unfollows(page)
            # Random break between major tasks for anti-detection
            logger.info("Taking a break between tasks...")
            random_sleep()
            process_followbacks(page)

            # Update cookies and schedule
            new_cookies = context.cookies()
            save_cookies(IG_USERNAME, new_cookies)
            update_schedule(IG_USERNAME)

        except Exception as e:
            logger.error(f"Error during execution: {e}")
            error_screenshot = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=error_screenshot)
            logger.info(f"Error screenshot saved: {error_screenshot}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
