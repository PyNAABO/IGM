# Instagram Automation Framework (IGM)

A modular, framework-style automation tool for Instagram interactions. Built with Python, Playwright, and Redis for high reliability and anti-detection.

## 🚀 Key Features

- **Modular Architecture**: Features are independent classes (Unfollow, Follow-back, etc.).
- **Session Persistence**: Secure cookie storage in Redis to avoid repetitive logins and bans.
- **Human-Like Behavior**: Random execution windows (2-5 hours), random action delays, and human-like scrolling/navigation.
- **Smart Logic**: Visits profiles individually to verify "Following" status before acting.
- **Extensible**: Easily add new features like Likers, Commenters, or DM automation.
- **GitHub Actions Ready**: Designed to run on a schedule without user intervention.

## 📂 Project Structure

```text
IGM/
├── igm/                    # Core Package
│   ├── core/               # System Logic
│   │   ├── bot.py          # Central IGMBot Class
│   │   ├── session.py      # Redis Session/Schedule Manager
│   │   ├── config.py       # Environment Configuration
│   │   └── utils.py        # Shared Utilities
│   ├── features/           # Automation Modules
│   │   ├── base.py         # Feature Base Class
│   │   ├── follow.py       # Follow-back Logic
│   │   ├── unfollow.py     # Unfollow Non-followers Logic
│   │   ├── like.py         # [Placeholder] Logic for liking posts
│   │   └── dm.py           # [Placeholder] Logic for sending DMs
│   └── __main__.py         # Package Entry Point
├── scripts/                # Helper Tools
│   ├── import_cookies.py   # Initial Login/Import Tool
│   └── debug_redis.py      # Connectivity Tester
├── run.py                  # Root Execution Script
├── requirements.txt        # Production Dependencies
└── README.md
```

## 🛠️ Setup & Installation

### 1. Prerequisites

- **Redis**: Use [Upstash](https://upstash.com/) for a free-tier managed Redis.
- **Python 3.10+**

### 2. Configuration

Create a `.env` file in the root directory:

```ssh
IG_USERNAME=your_username
IG_PASSWORD=your_password
REDIS_URL=redis://default:password@endpoint:port
```

> **Note**: `IG_USERNAME` and `IG_PASSWORD` are mandatory. The bot will validate these on startup.

### 3. Installation

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

### 4. Initial Run (Crucial)

You must import your session cookies from a logged-in browser once to avoid hitting the login wall:

```powershell
python -m scripts.import_cookies
```

### 5. Start the Bot

```powershell
python run.py
```

### 6. Force Run (Bypass Schedule)

To run the bot immediately regardless of the schedule (e.g., for testing), set `FORCE_RUN=true`:

On Windows (PowerShell):

```powershell
$env:FORCE_RUN="true"; python run.py
```

On Linux/Mac:

```bash
FORCE_RUN=true python run.py
```

## 🧩 Adding New Features

The modular design makes it easy to add new automation logic:

1. Create a new file in `igm/features/`, e.g., `like_hashtags.py`.
2. Inherit from `BaseFeature`:

   ```python
   from .base import BaseFeature

   class LikeHashtagsFeature(BaseFeature):
       def run(self):
           self.page.goto("https://www.instagram.com/explore/tags/coding/")
           # Your logic here...
   ```

3. Register it in `igm/__main__.py` or call it from `run.py`.

## 🔄 User Tracking System

The bot intelligently tracks which users have been processed to avoid checking the same accounts repeatedly:

- **Persistent Memory**: Uses Redis to remember who's been checked for 21 days (3 weeks)
- **Separate Tracking**: Follow and Unfollow features maintain independent tracking
- **Automatic Progress**: Each run processes new users, systematically working through your entire list
- **Auto-Reset**: After 3 weeks, all users become "unprocessed" again to catch status changes

**Example Flow:**

- Run 1: Checks users 1-10, marks them as processed
- Run 2: Automatically skips 1-10, checks users 11-20
- Run 3: Skips 1-20, checks users 21-30
- After 3 weeks: Reset, can re-check all users

This prevents the "Groundhog Day" problem where the bot would endlessly check the same 10 users.

## 🛡️ Anti-Detection Measures

- **User Agent**: Mimics a standard Windows Chrome 120 browser.
- **Random Breaks**: The bot sleeps between 10-30 seconds between actions.
- **Gap Schedules**: Bot only executes "real" cycles every 2-5 hours.
- **Session Re-use**: Avoids logging in from scratch, which is the #1 trigger for account flags.

## 🤝 Customization

- To change the frequency of runs, edit `igm/core/session.py` -> `update_schedule`.
- To adjust navigation timeouts, edit `igm/core/config.py`.
- To change the tracking reset period (default: 3 weeks), edit `PROCESSED_USER_EXPIRY_DAYS` in `igm/core/session.py`.

---

_Disclaimer: Use this tool responsibly. Automation against Instagram's TOS can lead to account suspension._
