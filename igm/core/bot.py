import sys
import os
import time
import random
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .config import IG_USERNAME, TIMEOUT_NAVIGATION, USER_AGENT
from .session import load_cookies, save_cookies, check_schedule, update_schedule
from .utils import random_sleep

# Configure logging (can be enhanced later)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("IGMBot")


class IGMBot:
    def __init__(self):
        self.username = IG_USERNAME
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

        if not self.username:
            logger.error("IG_USERNAME not set.")
            sys.exit(1)

    def start(self, headless=True):
        """Initializes the browser and context."""
        # Check for force run flag
        force_run = os.getenv("FORCE_RUN", "false").lower() == "true"

        # Check Schedule first (unless forced)
        if not force_run and not check_schedule(self.username):
            logger.info("Schedule check failed (too early). Exiting.")
            return False

        logger.info("Starting IGMBot...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(user_agent=USER_AGENT)

        self._load_session()
        self.page = self.context.new_page()

        # Create screenshots directory
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        return True

    def _load_session(self):
        """Loads cookies from Redis."""
        cookies = load_cookies(self.username)
        if cookies:
            logger.info(f"Loading {len(cookies)} cookies from Redis.")
            self.context.add_cookies(cookies)
        else:
            logger.info("No cookies found in Redis. Starting fresh.")

    def login(self):
        """Navigates to Instagram and checks login status."""
        try:
            logger.info("Navigating to Instagram...")
            try:
                self.page.goto(
                    "https://www.instagram.com/",
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT_NAVIGATION,
                )
            except PlaywrightTimeoutError:
                logger.error("Navigation timed out. Internet might be slow or down.")
                return False
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                return False

            time.sleep(5)

            # Critical: Validate session before any actions
            if self.page.locator("input[name='username']").count() > 0:
                logger.error(
                    "CRITICAL: Login form detected. Session invalid or expired."
                )
                logger.error("Please run: python -m scripts.import_cookies")
                self.screenshot("error_session_invalid")
                self.close()
                sys.exit(1)

            logger.info("Login check successful.")
            return True

        except Exception as e:
            logger.error(f"Error during login/navigation: {e}")
            self.screenshot("error_login")
            return False

    def run_feature(self, feature_class):
        """Executes a given feature class."""
        feature_name = feature_class.__name__
        logger.info(f"Running feature: {feature_name}")
        try:
            feature = feature_class(self)
            feature.run()
        except Exception as e:
            logger.error(f"Error executing feature {feature_name}: {e}")
            self.screenshot(f"error_feature_{feature_name}")

    def screenshot(self, name):
        """Takes a timestamped screenshot."""
        filename = f"screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if self.page:
            self.page.screenshot(path=filename)
            logger.info(f"Screenshot saved: {filename}")

    def close(self):
        """Closes the browser and updates session/schedule."""
        if self.context:
            try:
                new_cookies = self.context.cookies()
                save_cookies(self.username, new_cookies)
                update_schedule(self.username)
                logger.info("Session saved and schedule updated.")
            except Exception as e:
                logger.error(f"Error saving session: {e}")

        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("IGMBot closed.")

    def random_sleep(self, min_seconds=2, max_seconds=5):
        # Wrapper around utils.random_sleep for backward compatibility in features if needed
        # But features should ideally use self.bot.random_sleep or import directly
        random_sleep(min_seconds, max_seconds)
