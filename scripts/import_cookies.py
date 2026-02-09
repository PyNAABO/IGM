from iaf.core.config import IG_USERNAME
from iaf.core.session import save_cookies
from urllib.parse import unquote


def import_cookies():
    print(
        "Since we are switching to Playwright, we need to import your browser cookies."
    )
    print("1. Open Instagram in your browser (where you are logged in).")
    print("2. Open Developer Tools (F12) -> Application tab (or Storage).")
    print("3. Look for 'Cookies' -> 'https://www.instagram.com'.")
    print("4. Find the cookie named 'sessionid'.")
    print("5. Copy its Value.")

    sessionid = input("\nPaste your 'sessionid' Value here: ").strip()
    sessionid = unquote(sessionid)

    if not sessionid:
        print("No sessionid provided.")
        return

    # Validate sessionid format
    # Format: user_id:random_string:verification or user_id%3Arandom_string%3Averification
    import re

    if not re.match(r"^\d+(%3A|:)[\w-]+(%3A|:)[\w-]+$", sessionid):
        print("ERROR: Invalid sessionid format.")
        print("Expected format: user_id:random_string:verification")
        print("Example: 1234567890:abc123xyz:1")
        return

    # Extract user_id (optional, but good to have)
    user_id = None
    try:
        # Session ID format is usually: user_id%3Arandom_string%3Averification
        # We try to extract the user_id
        parts = sessionid.split(":") if ":" in sessionid else sessionid.split("%3A")
        if len(parts) > 1 and parts[0].isdigit():
            user_id = parts[0]
            print(f"Extracted User ID: {user_id}")
    except Exception:
        print("Could not extract user_id. Proceeding anyway.")

    # Create Playwright-compatible cookie list
    cookies = [
        {
            "name": "sessionid",
            "value": sessionid,
            "domain": ".instagram.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax",
        }
    ]

    if user_id:
        cookies.append(
            {
                "name": "ds_user_id",
                "value": user_id,
                "domain": ".instagram.com",
                "path": "/",
                "secure": True,
            }
        )

    # Save to Redis using the new session manager
    if save_cookies(IG_USERNAME, cookies):
        print("Session cookies saved to Redis successfully (Playwright format)!")
        print("Now run 'playwright install chromium' and then 'python run.py'.")
    else:
        print("Failed to save cookies to Redis. Check your configuration.")


if __name__ == "__main__":
    import_cookies()
