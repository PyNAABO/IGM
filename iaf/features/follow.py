import time
import random
from .base import BaseFeature
from iaf.core.config import (
    TIMEOUT_MODAL,
    get_counts_from_page,
    calculate_actions_per_run,
    MIN_DELAY_BETWEEN_ACTIONS,
    MAX_DELAY_BETWEEN_ACTIONS,
    PROCESSED_USER_EXPIRY_DAYS,
)
from iaf.core.session import filter_unprocessed_users, mark_user_processed, is_user_processed


class FollowFeature(BaseFeature):
    def run(self):
        """Follows users back (Fans)."""
        username = self.bot.username

        # Get follower count for dynamic calculations
        follower_count, _ = get_counts_from_page(self.page, username)
        if follower_count:
            self.logger.info(f"Account has {follower_count} followers.")
        else:
            self.logger.warning("Could not retrieve follower count.")

        # Calculate safe actions per run based on account size
        actions_per_run = calculate_actions_per_run(follower_count, 0, "follow")
        self.logger.info(f"Targeting {actions_per_run} actions per run (complete in ~{PROCESSED_USER_EXPIRY_DAYS} days).")

        self.logger.info("Checking 'Followers' list for fans...")

        self.page.goto(
            f"https://www.instagram.com/{username}/", wait_until="domcontentloaded"
        )
        time.sleep(3)

        try:
            self.page.locator(f"a[href='/{username}/followers/']").click()
            self.page.wait_for_selector("div[role='dialog']", timeout=TIMEOUT_MODAL)
        except Exception as e:
            self.logger.warning(f"Could not open 'Followers' dialog: {e}")
            return

        time.sleep(3)

        # Collect usernames by scrolling until we have enough unprocessed users
        targets = self.collect_unprocessed_users(username, "follow", actions_per_run)
        self.logger.info(f"Found {len(targets)} fans to check.")

        count = 0
        for user in targets:
            if count >= actions_per_run:
                break

            self.logger.info(f"Checking {user}...")
            try:
                if self.process_single_user(user):
                    count += 1
                # Mark as processed regardless of outcome
                mark_user_processed(username, user, "follow")
            except Exception as e:
                self.logger.error(f"Error checking {user}: {e}")
                # Still mark as processed to avoid retrying failed users
                mark_user_processed(username, user, "follow")

            # Conservative delay between actions
            time.sleep(random.uniform(MIN_DELAY_BETWEEN_ACTIONS, MAX_DELAY_BETWEEN_ACTIONS))

        self.logger.info(f"Followed back {count} users.")

    def process_single_user(self, user):
        self.page.goto(
            f"https://www.instagram.com/{user}/", wait_until="domcontentloaded"
        )
        self.sleep(3, 6)

        # 1. Check if WE already follow THEM
        if (
            self.page.locator("button").filter(has_text="Following").count() > 0
            or self.page.locator("button").filter(has_text="Requested").count() > 0
        ):
            self.logger.info(f"Already following {user}. Skipping.")
            return False

        # 2. Check for "Follow Back" button
        if self.page.locator("button").filter(has_text="Follow Back").count() > 0:
            self.logger.info(f"Found 'Follow Back' button for {user}. Following...")
            self.page.locator("button").filter(has_text="Follow Back").first.click()
            self.sleep()
            return True

        # 3. Check for "Follows you" badge
        if self.page.get_by_text("Follows you").count() > 0:
            self.logger.info(f"{user} follows you (badge detected). Following back...")
            follow_btn = self.page.locator("button").filter(has_text="Follow").first
            if follow_btn.count() > 0:
                follow_btn.click()
                self.sleep()
                return True

        self.logger.info(
            f"{user} found in followers list but no indicator on profile. Skipping."
        )
        return False

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
