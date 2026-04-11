# Clash Royale Clan Bot

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![Discord.py](https://img.shields.io/badge/discord.py-2.3.0+-blue.svg)
![Database](https://img.shields.io/badge/database-SQLite-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

A comprehensive moderation and statistics bot that integrates with the Clash Royale API to simplify clan management via Discord. It includes war tracking, activity scoring, achievement systems, deck suggestions, record tracking, and automated reporting.

## Table of Contents
- [Features](#features)
- [Multi-Language (i18n) System](#multi-language-i18n-system)
- [Installation & Configuration](#installation--configuration)
- [Command List](#command-list)
- [Project Structure](#project-structure)
- [Automated Tasks](#automated-tasks)
- [Database](#database)
- [Security](#security)
- [Contributing](#contributing)

---

## Features

### War and Clan Management
* **River Race Tracking:** Active war status, clan ranking, and deck usage.
* **Contribution Ranking:** Medal-based member performance tracking.
* **War History:** Detailed summary of the last 5 clan wars.
* **Non-Participants List:** Instantly identify members with 0 medals.
* **War Reminder:** Automatic warning system near the end time.
* **Member Tag List:** View all clan members' names and tags with the `!tags` command.

### Member Tracking
* **Smart Join/Leave Detection:** Automatically differentiates between members who left and were kicked.
  * 🟡 Moved to another clan → **"left"** (with new clan name)
  * 🔴 No clan → **"kicked"**
  * 🟢 Joined → **"joined"**

### Activity and Analysis
* **Activity Score (0-100):** Automatic calculation using Donations (30%) + War (50%) + Trophies (20%).
* **Kick List:** Customizable recommendation list of members with the lowest scores.
* **Promotion Suggestions:** Statistically determined Elder/Co-Leader candidates.
* **Visual Analysis:** Fame history comparison charts using `matplotlib`.
* **Prediction System:** War result probability calculation using Normal Distribution.

### Achievement and Badge System
* **9 Different Badges:** First Blood, Fire Streak, Donation King, MVP, Legend, and more.
* **Auto Check:** Members' badge status is evaluated every 6 hours.
* **Leaderboard:** Leaderboard for members with the most badges.

*(All other systems like deck suggester, profile analysis, clan records, and weekly reporting are fully integrated.)*

---

## Multi-Language (i18n) System

Clashbot supports a dynamic internationalization system. 

* **Default Language:** English (`en`).
* **Available Languages:** English (`en`), Turkish (`tr`).
* **Guild Preferences:** Each Discord server can set its own preferred language using the `!language` / `!dil` command.
* **Adding a Language:** To add a new language, create a new `[lang].json` file in the `locales/` directory, mirroring the structure of `en.json`.

---

## Installation & Configuration

### 1. Requirements
* Python 3.10+
* Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
* Clash Royale API Token ([Clash Royale Developer](https://developer.clashroyale.com)) *(Note: CR API is IP-based, don't forget to whitelist your server's IP address.)*

### 2. Installation Steps

```bash
# Clone the repo and enter the directory
git clone https://github.com/omerk-c/Clash-Royale-Clan-Bot
cd Clash-Royale-Clan-Bot

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # For Windows: .venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Create the environment variables file
cp .env.example .env
# Edit the .env file and enter your own token/key values
```

### 3. Configuration (.env)

Edit your `.env` file as follows:

```env
# Discord Bot Token – Obtained from Discord Developer Portal
DISCORD_TOKEN=your_discord_bot_token

# Clash Royale API Key – Obtained from https://developer.clashroyale.com
CR_API_KEY=your_clash_royale_api_token

# Clan Tag – Written including the # sign
CLAN_TAG=#YOURCLANTAG

# Default notification channel ID
CHANNEL_ID=discord_channel_id

# Leader Role ID – Required for permission checks (Copy the role ID with Developer Mode on)
LEADER_ROLE_ID=discord_leader_role_id
```

> **⚠️ Important:** If `LEADER_ROLE_ID` is not set, only users with Discord Administrator permissions can use bot management commands (`!grant_perm`, `!revoke_perm`). This value must be entered correctly to authorize via the Leader role.

To start the bot:

```bash
# With the virtual environment active:
python3 main.py

# Or directly with Python in the virtual environment:
.venv/bin/python3 main.py
```

---

## Command List

Click on the headers to see details:

<details>
<summary><strong>War and Leadership</strong></summary>

| Command | Description |
| --- | --- |
| `!clan` | Clan general info |
| `!list` | Member list + ranks |
| `!tags` | Member names and Clash Royale tags |
| `!wars` | River race status |
| `!contribution` | Contribution ranking (top 10) |
| `!non_participants` | 0 medal members |
| `!warlog` | Last 5 wars summary |

</details>

<details>
<summary><strong>Statistics and Profile</strong></summary>

| Command | Description |
| --- | --- |
| `!profile [#TAG/@mention]` | Detailed player profile |
| `!activity` | Activity score for all members (0-100) |
| `!kicklist [number]` | Lowest-score N people (default 5) |
| `!promotion` | Elder/Co-Leader promotion suggestion |
| `!graph` | Fame history line chart |
| `!predict [extra]` | War result prediction (Normal Distribution) |

</details>

<details>
<summary><strong>Badges and Decks</strong></summary>

| Command | Description |
| --- | --- |
| `!mybadges [#TAG]` | Earned badges |
| `!badge_leaderboard` | Badge leaderboard |
| `!suggest_deck [arena]` | Meta deck by arena |
| `!random_deck` | Random fun deck |
| `!analyzer #TAG` | Player deck/card usage analysis |

</details>

<details>
<summary><strong>Channel Management</strong></summary>

| Command | Description |
| --- | --- |
| `!channel_set <type> #channel` | Assign a notification channel |
| `!channel_remove <type>` | Remove a channel assignment |
| `!channel_list` | Show all channel assignments |
| `!channel_test <type/all>` | Send a test message |

</details>

<details>
<summary><strong>System and Management</strong></summary>

| Command | Description |
| --- | --- |
| `!weekly` | Instant weekly report |
| `!weekly_setting` | Toggle automatic report |
| `!records` | All clan records |
| `!language <en/tr>` | Change guild language |
| `!grant_perm @person` | Grant bot permission (Leader/Admin only) |
| `!revoke_perm @person` | Revoke bot permission (Leader/Admin only) |
| `!help` | Lists all commands |

</details>

---

## Project Structure

```text
clashbot/
├── cogs/                        # Modular bot commands
│   ├── achievements.py          # Achievement badge system
│   ├── activity.py              # Activity score and kick list
│   ├── auth.py                  # Authorization and access control
│   ├── battle_history.py        # Battle history analysis
│   ├── channel_manager.py       # Notification channel management
│   ├── deck_suggest.py          # Meta deck suggester
│   ├── donations.py             # Donation tracking
│   ├── prediction.py            # War result prediction
│   ├── profile.py               # Player profile analysis
│   ├── promotion.py             # Promotion suggestions
│   ├── records.py               # Clan records
│   ├── scraper.py               # RoyaleAPI web scraping
│   ├── settings.py              # Server settings & language
│   ├── stats.py                 # Statistical charts
│   ├── tracker.py               # Change tracking & member join/leave
│   ├── war.py                   # War commands, member tags, reminders
│   └── weekly_report.py         # Weekly report
├── data/                        # Auto-created on first run (in .gitignore)
│   ├── clashbot.db              # Main SQLite database
│   ├── authorized_users.json    # Authorized user list
│   ├── channel_config.json      # Channel configuration
│   ├── clan_records.json        # Clan records
│   └── linked_accounts.json     # Discord-CR account maps
├── utils/                       # Utility tools and API managers
│   ├── channels.py              # Channel management module
│   ├── config.py                # .env reading and settings
│   ├── cr_api.py                # Clash Royale API requests
│   ├── database.py              # SQLite wrapper
│   └── i18n.py                  # Internationalization engine
├── locales/                     # Language files
│   ├── en.json                  # English string mapping
│   └── tr.json                  # Turkish string mapping
├── main.py                      # Bot main entry point
├── check.py                     # Locale key parity checker
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables file
└── .env                         # Environment variables (not in git)
```

> **Note:** The `data/` folder is automatically created when the bot runs for the first time. This folder is included in `.gitignore` and is not added to the repo.

---

## Automated Tasks

| Task | Frequency | Description |
| --- | --- | --- |
| **Change Tracking** | 10 min | Detects donation/war changes |
| **Member Join/Leave** | 2 min | Reports joined/left/kicked members |
| **War Reminder** | 30 min | Deck warning near end time |
| **Batched Report** | 60 min | Sends collected changes as a single embed |
| **Periodic Clan Report** | 2 hours | Clan status summary |
| **Activity Score** | 6 hours | Saves all members' scores to the database |
| **Weekly Report** | Mon 08:00 | Sends automatic performance report (UTC) |

---

## Database

The bot uses `aiosqlite` to ensure data integrity and optimize asynchronous I/O operations. The database (`data/clashbot.db`) is automatically created on first startup.

* **`players`:** Player snapshot data (trophies, level, donations, etc.)
* **`donation_history` & `war_history`:** Weekly performance records.
* **`activity_log`:** Daily activity score (for time series analysis).
* **`trophy_snapshots`:** Daily trophy snapshots.
* **`achievements`:** Earned player badges.
* **`server_settings`:** Guild-specific configurations such as preferred language.

---

## Security

The bot includes the following security measures:

* **SQL Injection Protection:** Allowed column names in database queries are checked against a whitelist.
* **Role-Based Authorization:** Leader permission is verified via the Discord Role ID rather than text-based role names (spoofing protection).
* **Concurrency Safety:** JSON file operations are protected with `asyncio.Lock` and `threading.Lock` to prevent data loss.
* **API Token Security:** Sensitive information is stored in the `.env` file and excluded from version control via `.gitignore`.

---

## Contributing

1. Fork the repo.
2. Create a new feature branch (`git checkout -b feature/new-feature`).
3. Commit your changes (`git commit -m 'feat: added new feature'`).
4. Push your branch (`git push origin feature/new-feature`).
5. Open a Pull Request.
