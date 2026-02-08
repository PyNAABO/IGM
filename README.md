# Instagram Automation Bot

This project automates Instagram interactions using GitHub Actions, with secure session persistence via Redis to avoid login bans.

## Setup

### 1. Prerequisites

- **GitHub Account**: To host the repository and run Actions.
- **Instagram Account**: Credentials for the bot.
- **Redis Database**: Use [Upstash Redis](https://upstash.com/) (Free Tier) for session storage.

### 2. GitHub Secrets

Go to your repository **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.

Add the following secrets:

- `IG_USERNAME`: Your Instagram username.
- `IG_PASSWORD`: Your Instagram password.
- `REDIS_URL`: Your Redis connection string (e.g., `redis://default:password@endpoint:port`).

### 3. Usage

The bot is configured to run automatically:

- **Frequent Check**: Runs every **30 minutes** (configurable in `.github/workflows/instagram_bot.yml`).
- **Random Execution**: Acts like a human by only executing "real" actions every **4-8 hours** (randomly determined). If it wakes up too early, it checks the schedule and goes back to sleep.
- **Manually**: Go to **Actions** tab -> **Instagram Automation Bot** -> **Run workflow**.

## Features

- **Session Persistence**: Uses Redis to store session cookies, preventing repeated logins and bans.
- **Browser Automation (Playwright)**: Mimics a real user on a Chrome browser.
- **Smart Unfollow**: Checks your "Following" list, visits profiles individually, and correctly unfollows users who don't follow you back.
- **Smart Follow Back**: Checks your "Followers" list and follows back your fans.
- **Human-Like Limits**: Executes up to **10 actions per run** to stay well under Instagram's rate limits.
- **Anti-Detection**: Random sleep intervals between actions (10-30 seconds).
- **Session Validation**: Automatically detects expired sessions and exits safely to prevent anti-bot triggers.

## Security Features

- ✅ **Redis Connection Timeouts**: 5-second timeouts prevent hanging connections
- ✅ **Safe Defaults**: Bot won't run if Redis is unavailable (prevents rate-limit violations)
- ✅ **Session Validation**: Checks for valid login before any actions
- ✅ **Race Condition Protection**: Waits for modals to appear before clicking
- ✅ **Input Validation**: Validates sessionid format during cookie import
- ✅ **Timestamped Error Logs**: Error screenshots include timestamps for debugging

## Local Development

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    python -m playwright install chromium
    ```
3.  Create a `.env` file based on `config.py`:
    ```ini
    IG_USERNAME=your_username
    IG_PASSWORD=your_password
    REDIS_URL=redis://...
    ```
4.  **Import Cookies** (Required for first run):
    ```bash
    python import_cookies.py
    ```
5.  Run the bot:
    ```bash
    python main.py
    ```

> **Note**: If Redis is unavailable, the bot will skip execution by default for safety. Ensure your Redis connection is working for automation to proceed.

## Customization

Edit `main.py` to add your custom automation logic inside the `try/except` block at the end of the `main()` function.

## Development Dependencies

For testing and development, install additional dependencies:

```bash
pip install -r requirements-dev.txt
```
