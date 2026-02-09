import time
import random
from .base import BaseFeature
from iaf.core.config import (
    TIMEOUT_MODAL,
    TIMEOUT_ACTION,
    get_counts_from_page,
    calculate_actions_per_run,
    MIN_DELAY_BETWEEN_ACTIONS,
    MAX_DELAY_BETWEEN_ACTIONS,
    PROCESSED_USER_EXPIRY_DAYS,
)
from iaf.core.session import filter_unprocessed_users, mark_user_processed, is_user_processed


class UnfollowFeature(BaseFeature):
    def run(self):
        """Unfollows users who don't follow back."""
        username = self.bot.username

        # Get following count for dynamic calculations
        _, following_count = get_counts_from_page(self.page, username)
        if following_count:
            self.logger.info(f"Account is following {following_count} users.")
        else:
            self.logger.warning("Could not retrieve following count.")

        # Calculate safe actions per run based on account size
        actions_per_run = calculate_actions_per_run(0, following_count, "unfollow")
        self.logger.info(f"Targeting {actions_per_run} actions per run (complete in ~{PROCESSED_USER_EXPIRY_DAYS} days).")

        self.logger.info("Checking 'Following' list for non-followers...")

        # Go to profile
        self.page.goto(
            f"https://www.instagram.com/{username}/", wait_until="domcontentloaded"
        )
        time.sleep(3)

        # Open Following modal
        try:
            self.page.locator(f"a[href='/{username}/following/']").click()
            self.page.wait_for_selector("div[role='dialog']", timeout=TIMEOUT_MODAL)
        except Exception as e:
            self.logger.warning(f"Could not open 'Following' dialog: {e}")
            return

        time.sleep(3)

        # Collect usernames by scrolling until we have enough unprocessed users
        targets = self.collect_unprocessed_users(username, "unfollow", actions_per_run)
        self.logger.info(f"Found {len(targets)} users to check.")

        count = 0
        for user in targets:
            if count >= actions_per_run:
                break

            self.logger.info(f"Checking {user}...")
            try:
                if self.process_single_user(user):
                    count += 1
                # Mark as processed regardless of outcome
                mark_user_processed(username, user, "unfollow")
            except Exception as e:
                self.logger.error(f"Error checking {user}: {e}")
                # Still mark as processed to avoid retrying failed users
                mark_user_processed(username, user, "unfollow")

            # Conservative delay between actions
            time.sleep(random.uniform(MIN_DELAY_BETWEEN_ACTIONS, MAX_DELAY_BETWEEN_ACTIONS))

        self.logger.info(f"Unfollow cycle verify complete.")

    def process_single_user(self, user):
        # We need to navigate to user profile
        self.page.goto(
            f"https://www.instagram.com/{user}/", wait_until="domcontentloaded"
        )
        self.sleep(3, 6)

        follows_you = self.check_if_follows_me(user)

        if not follows_you:
            self.logger.info(f"{user} does NOT follow you. Unfollowing...")
            self.perform_unfollow(user)
            return True
        else:
            self.logger.info(f"{user} follows you. Keeping.")
            return False

    def check_if_follows_me(self, user):
        # 1. "Follow Back" button?
        if self.page.locator("button").filter(has_text="Follow Back").count() > 0:
            self.logger.info(f"'Follow Back' button found for {user}. They follow you!")
            return True

        # 2. "Follows you" badge?
        if self.page.locator("div").filter(has_text="Follows you").count() > 0:
            # Note: Original code used page.get_by_text("Follows you"), checking div for robustness
            # Resetting to original logic to be safe
            pass
        if self.page.get_by_text("Follows you").count() > 0:
            self.logger.info(f"'Follows you' badge found for {user}.")
            return True

        # 3. Deep check in their following list
        return self.deep_check_follows_me(user)

    def deep_check_follows_me(self, user):
        self.logger.info(f"Performing deep check in {user}'s Following list...")
        try:
            following_link = self.page.locator(f"a[href*='/{user}/following/']")
            if following_link.count() > 0:
                following_link.click()
                self.sleep(2, 4)

                # Search for myself
                search_input = self.page.locator(
                    "div[role='dialog'] input[placeholder='Search']"
                )
                if search_input.count() > 0:
                    search_input.fill(self.bot.username)
                    self.sleep(2, 4)

                    my_profile = self.page.locator(
                        f"div[role='dialog'] a[href='/{self.bot.username}/']"
                    )
                    if my_profile.count() > 0:
                        self.logger.info(f"Found myself in {user}'s following list.")
                        self._close_dialog()
                        return True
                    else:
                        self.logger.info(
                            f"Did NOT find myself in {user}'s following list."
                        )

                self._close_dialog()
        except Exception as e:
            self.logger.warning(f"Deep check failed: {e}")

        return False

    def _close_dialog(self):
        self.page.keyboard.press("Escape")
        try:
            self.page.locator("div[role='dialog']").wait_for(
                state="hidden", timeout=TIMEOUT_MODAL
            )
        except:
            # Fallback close
            self.page.mouse.click(10, 10)

    def perform_unfollow(self, user):
        # Look for "Following" button
        following_btn = self.page.locator("button").filter(has_text="Following").first
        if following_btn.count() > 0:
            following_btn.click()
            self.sleep(1, 2)

            try:
                unfollow_confirm = self.page.get_by_role("button", name="Unfollow")
                unfollow_confirm.wait_for(state="visible", timeout=TIMEOUT_ACTION)
                unfollow_confirm.click()
                self.logger.info(f"Successfully unfollowed {user}")
                self.sleep()
            except Exception as e:
                self.logger.warning(f"Failed to confirm unfollow: {e}")
        else:
            self.logger.warning("Could not find 'Following' button.")

    def collect_unprocessed_users(self, username, feature_type, actions_per_run):
        """Scrolls through the modal and collects usernames until we have enough unprocessed users."""
        collected = []
        processed = set()
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 100

        dialog = self.page.locator("div[role='dialog']")

        while len(collected) < actions_per_run and scroll_attempts < max_scroll_attempts:
            # Extract current visible usernames
            links = dialog.locator("a[role='link'][href^='/']").all()
            if not links:
                links = dialog.locator("a[href^='/']").all()

            for link in links:
                href = link.get_attribute("href")
                if href and href.count("/") == 2:
                    user = href.strip("/")
                    if user != username and user not in processed:
                        processed.add(user)
                        # Check if already processed
                        if not is_user_processed(username, user, feature_type):
                            collected.append(user)
                            if len(collected) >= actions_per_run:
                                break

            if len(collected) >= actions_per_run:
                break

            # Try scrolling
            try:
                scroll_container = dialog.locator("div").last
                scroll_container.scroll_into_view_if_needed()
                time.sleep(2)
                scroll_attempts += 1

                # Check if we reached the end (no new users loaded)
                current_count = len(collected)
                if current_count == last_count:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_count = current_count

            except Exception:
                scroll_attempts += 1

        return collected[:actions_per_run]
