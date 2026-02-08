import time
import random
from app.utils import get_logger, random_sleep
from app.config import IG_USERNAME, TIMEOUT_ACTION, TIMEOUT_MODAL

logger = get_logger(__name__)

MAX_ACTIONS_PER_RUN = 10


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
        page.wait_for_selector("div[role='dialog']", timeout=TIMEOUT_MODAL)
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
                        try:
                            # Wait for dialog to close
                            page.locator("div[role='dialog']").wait_for(
                                state="hidden", timeout=TIMEOUT_MODAL
                            )
                        except Exception:
                            logger.warning(
                                "Dialog didn't close with Escape, trying click outside/close button."
                            )
                            # Fallback: clicking the close button if available
                            close_btn = (
                                page.locator("div[role='dialog']")
                                .get_by_role("button")
                                .first
                            )
                            if close_btn.count() > 0:
                                close_btn.click()
                            else:
                                # Click coordinates (top left) to dismiss if possible, or reload page
                                page.mouse.click(10, 10)

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
                # Using a more robust selector that targets the specific button style or text
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
                        unfollow_confirm.wait_for(
                            state="visible", timeout=TIMEOUT_ACTION
                        )
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
        page.wait_for_selector("div[role='dialog']", timeout=TIMEOUT_MODAL)
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

            # 1. Check if WE already follow THEM.
            # Button usually says "Following" or "Requested"
            if (
                page.locator("button").filter(has_text="Following").count() > 0
                or page.locator("button").filter(has_text="Requested").count() > 0
            ):
                logger.info(f"Already following {user}. Skipping.")
                continue

            # 2. If we don't follow them, check if they follow us so we can 'Follow Back'
            # Look for "Follow Back" button - this is the strongest signal
            if page.locator("button").filter(has_text="Follow Back").count() > 0:
                logger.info(f"Found 'Follow Back' button for {user}. Following...")
                page.locator("button").filter(has_text="Follow Back").first.click()
                count += 1
                random_sleep()
                continue

            # 3. If generic "Follow" button, check for "Follows you" badge text
            if page.get_by_text("Follows you").count() > 0:
                logger.info(f"{user} follows you (badge detected). Following back...")

                # Click generic Follow button
                follow_btn = page.locator("button").filter(has_text="Follow").first
                if follow_btn.count() > 0:
                    follow_btn.click()
                    count += 1
                    random_sleep()
                else:
                    logger.warning(f"Could not find 'Follow' button for {user}")
                continue

            # 4. If we reached here, they appear in our followers list but:
            # - We don't follow them
            # - No "Follow Back" button
            # - No "Follows you" badge
            # This is ambiguous. Safest is to skip or assume the list was correct.
            # Given the user feedback, we will log this specific state.
            logger.info(
                f"{user} in followers list but no 'Follows you' indicator found on profile. Skipping to be safe."
            )

        except Exception as e:
            logger.error(f"Error checking {user}: {e}")

    logger.info(f"Followed back {count} users.")
