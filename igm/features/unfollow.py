import time
import random
from .base import BaseFeature
from igm.core.config import TIMEOUT_MODAL, TIMEOUT_ACTION, MAX_ACTIONS_PER_RUN
from igm.core.session import filter_unprocessed_users, mark_user_processed


class UnfollowFeature(BaseFeature):
    def run(self):
        """Unfollows users who don't follow back."""
        self.logger.info("Checking 'Following' list for non-followers...")
        username = self.bot.username

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

        # Extract usernames
        links = self.page.locator("div[role='dialog'] a[role='link'][href^='/']").all()
        if not links:
            links = self.page.locator("div[role='dialog'] a[href^='/']").all()

        usernames = []
        for link in links:
            href = link.get_attribute("href")
            if href and href.count("/") == 2:
                user = href.strip("/")
                if user != username:
                    usernames.append(user)

        # Filter unique and slice
        all_usernames = list(set(usernames))

        # Filter out already-processed users
        unprocessed_users = filter_unprocessed_users(
            username, all_usernames, "unfollow"
        )
        targets = unprocessed_users[:MAX_ACTIONS_PER_RUN]

        self.logger.info(
            f"Found {len(targets)} users to check (out of {len(all_usernames)} visible)."
        )

        count = 0
        for user in targets:
            if count >= MAX_ACTIONS_PER_RUN:
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
