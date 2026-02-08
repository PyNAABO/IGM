import sys
import time
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from app.config import IG_USERNAME, IG_PASSWORD
from app.session_manager import (
    load_cookies,
    save_cookies,
    check_schedule,
    update_schedule,
)
from app.config import TIMEOUT_NAVIGATION
from app.utils import get_logger, random_sleep
from app.actions import process_unfollows, process_followbacks

logger = get_logger(__name__)


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

        # Create screenshots directory if it doesn't exist
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        try:
            logger.info("Navigating to Instagram...")
            try:
                page.goto(
                    "https://www.instagram.com/",
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT_NAVIGATION,
                )
            except Exception as e:
                logger.warning(f"Navigation timeout: {e}")

            time.sleep(5)

            # Critical: Validate session before any actions
            if page.locator("input[name='username']").count() > 0:
                logger.error(
                    "CRITICAL: Login form detected. Session invalid or expired."
                )
                logger.error("Please run: python -m scripts.import_cookies")
                page.screenshot(
                    path=f"screenshots/error_session_invalid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
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
            error_screenshot = (
                f"screenshots/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            page.screenshot(path=error_screenshot)
            logger.info(f"Error screenshot saved: {error_screenshot}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
