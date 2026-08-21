<div align="center">

# 🛡️ Clash Royale Clan Bot

**A comprehensive Discord bot that automates clan management: war tracking, activity scoring, an achievement/badge system, and automated weekly reporting.**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Discord.py](https://img.shields.io/badge/discord.py-2.3.0+-blue.svg)
![Database](https://img.shields.io/badge/database-SQLite-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

</div>

---

> ⚠️ **Built for a single clan / single server.** The bot runs against one `CLAN_TAG` from `.env`, and notification channels are stored bot-wide rather than per-guild. If added to multiple Discord servers, only the language preference is per-guild — clan data and channel assignments are shared across all of them.

## 📋 Table of Contents

- [Features](#-features)
- [Authorization Model](#-authorization-model)
- [Installation](#-installation)
- [Command List](#-command-list)
- [Multi-Language (i18n)](#-multi-language-i18n)
- [Project Structure](#-project-structure)
- [Automated Tasks](#-automated-tasks)
- [Database](#-database)
- [Known Limitations](#-known-limitations)
- [Contributing](#-contributing)

---

## ✨ Features

### ⚔️ War & Clan Management
- Active River Race status, clan ranking, deck usage
- Contribution ranking (medal-based)
- Summary of the last 5 wars
- List of non-participating (0-medal) members
- Member tag/name listing

### 👥 Member Tracking
- Automatic join/leave detection (checks the API to see whether a departing member moved to another clan)
  - 🟡 Moved to another clan → reported with the new clan's name
  - 🔴 No clan → flagged as "kicked"
  - 🟢 New join

### 📊 Activity & Analysis
- **Activity Score (0-100):** Donations (30%) + War (50%) + Trophies (20%)
- Customizable list of low-scoring members
- Statistically-driven Elder/Co-Leader promotion suggestions
- Clan vs. opponent comparison chart via `matplotlib`
- War outcome prediction based on a normal distribution

### 🏅 Badge System
- 9 different badges (First Blood, Fire Streak, Donation King, MVP, Legend, etc.)
- Automatic check every 6 hours
- Leaderboard ranked by badge count

### 🃏 Decks & Other Tools
- Deck suggestions by arena level, random fun decks
- Per-player deck/card usage analysis
- Clan records and record-breaking history
- Automatic/manual weekly performance report

---

## 🔐 Authorization Model

This bot is **locked by default.** Once added to a server, no command works for anyone outside these three groups:

1. Members with Discord **Administrator** permission
2. Members holding the role set as `LEADER_ROLE_ID` in `.env`
3. Users explicitly authorized via `!grant_auth`

> This isn't limited to management commands like `grant_auth`/`revoke_auth` — **every command**, including read-only ones like `!clan` or `!wars`, goes through this check. If nothing seems to respond after inviting the bot, it's most likely because `LEADER_ROLE_ID` isn't set and the user isn't an Administrator.

| Command | Description | Who can use it |
| --- | --- | --- |
| `!grant_auth @member` (`!yetki_ver`) | Grants a user permission to use the bot | Admin / Leader |
| `!revoke_auth @member` (`!yetki_al`) | Revokes a user's permission | Admin / Leader |

---

## 🚀 Installation

### 1. Requirements

- Python 3.10+
- Discord Bot Token — [Discord Developer Portal](https://discord.com/developers/applications)
- Clash Royale API Token — [Clash Royale Developer Portal](https://developer.clashroyale.com)
  *(The CR API is IP-based — don't forget to whitelist your server's IP address.)*

### 2. Installation Steps

```bash
# Clone the repo
git clone https://github.com/omerk-c/Clash-Royale-Clan-Bot
cd Clash-Royale-Clan-Bot

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip3 install -r requirements.txt

# Create the environment variables file
cp .env.example .env
# Edit .env with your own token/key values
```

### 3. Configuration (`.env`)

```env
# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token

# Clash Royale API Key
CR_API_KEY=your_clash_royale_api_token

# Clan tag (including the # sign)
CLAN_TAG=#YOURCLANTAG

# Default notification channel ID
CHANNEL_ID=discord_channel_id

# Leader role ID (used for authorization)
LEADER_ROLE_ID=discord_leader_role_id
```

> ⚠️ If `LEADER_ROLE_ID` is left empty, only users with Discord **Administrator** permission can use the bot.

### 4. Start the Bot

```bash
python3 main.py
# or
.venv/bin/python3 main.py
```

---

## 📖 Command List

All commands use the `!` prefix; items in parentheses are Turkish aliases.

<details>
<summary><strong>⚔️ War & Clan</strong></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!clan` | `!klan` | General clan info |
| `!wars` | `!savaslar` | Active River Race status |
| `!contribution` | `!katki` | Contribution ranking (top 10) |
| `!warlog` | — | Summary of the last 5 wars |
| `!list` | `!liste` | Member list + roles |
| `!tags` | — | Member names and Clash Royale tags |
| `!inactive` | `!katilmayanlar`, `!sifircilar` | 0-medal members |

</details>

<details>
<summary><strong>📊 Stats & Profile</strong></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!profile [#TAG / @user]` | `!profil` | Detailed player profile |
| `!activity` | `!aktivite` | Activity score for all members (0-100) |
| `!kicklist [number]` | — | Lowest-scoring N members (default 5) |
| `!promotion` | `!terfi` | Elder/Co-Leader promotion suggestion |
| `!promotion_history #TAG` | `!terfi_gecmis` | A player's activity score history |
| `!graph` | `!grafik` | Clan vs. opponent fame history chart |
| `!player_board [#TAG]` | `!oyuncu_tablo` | Weekly war performance table |
| `!prediction [extra]` | `!tahmin` | War outcome prediction via normal distribution |
| `!battle_history [#TAG]` | `!savas_gecmisi` | Detailed analysis of the last 25 battles |
| `!deck_analysis #TAG` | `!deste_analiz` | Player deck/card usage analysis |

</details>

<details>
<summary><strong>🏅 Badges & Decks</strong></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!badges [#TAG]` | `!rozetlerim` | Earned badges |
| `!badge_leaderboard` | `!rozet_siralamasi` | Badge leaderboard |
| `!all_badges` | `!rozetler` | Descriptions of all badges |
| `!deck` | `!deste` | Random meta deck suggestion |
| `!suggest_deck [arena]` | `!deste_oner` | Meta deck suited to an arena level |
| `!random_deck` | `!deste_rastgele` | Completely random fun deck |
| `!meta` | — | Lists all meta decks |

</details>

<details>
<summary><strong>💰 Donations</strong></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!donations` | `!bagis` | Clan donation leaderboard |
| `!leechers` | `!somuruculer` | Members who donate below average but receive more |

</details>

<details>
<summary><strong>📢 Channel Management</strong> <sub>(requires Admin)</sub></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!set_channel <type> #channel` | `!kanal_ayar` | Assigns a notification channel |
| `!remove_channel <type>` | `!kanal_kaldir` | Removes a channel assignment |
| `!list_channels` | `!kanal_liste` | Shows all channel assignments |
| `!test_channel <type / all>` | `!kanal_test` | Sends a test message |

</details>

<details>
<summary><strong>🏆 Records & System</strong></summary>

| Command | Alias | Description |
| --- | --- | --- |
| `!records` | `!rekorlar` | All clan records |
| `!record_history [category]` | `!rekor_gecmis` | History of broken records |
| `!reset_record [category]` <sub>(Admin)</sub> | `!rekor_sifirla` | Resets records |
| `!weekly` | `!haftalik` | Instant weekly report |
| `!weekly_setting` | `!haftalik_ayar` | Toggles the automatic report on/off |
| `!language <en/tr>` | `!dil` | Changes the guild's language |
| `!grant_auth @member` <sub>(Admin/Leader)</sub> | `!yetki_ver` | Grants bot usage authorization |
| `!revoke_auth @member` <sub>(Admin/Leader)</sub> | `!yetki_al` | Revokes bot usage authorization |
| `!help` | `!yardim` | Lists all commands |

</details>

<details>
<summary><strong>🌐 RoyaleAPI Extras</strong> <sub>(experimental, web-scraping based)</sub></summary>

| Command | Description |
| --- | --- |
| `!royaleapi [#TAG]` | Fetches extra clan stats from the RoyaleAPI website |

> This command works outside the official Clash Royale API, by reading the HTML/internal structure of RoyaleAPI and similar third-party sites. It can break without warning whenever those sites change. On failure it simply returns a "couldn't fetch data" message — it won't crash the bot.

</details>

---

## 🌍 Multi-Language (i18n)

- **Default language:** English (`en`)
- **Available languages:** English (`en`), Turkish (`tr`)
- Each Discord server can set its own language preference with `!language` / `!dil`; the preference is stored per-guild in the database.
- To add a new language, create a `[lang].json` file in `locales/` that mirrors the structure of `en.json` exactly. The `check.py` script verifies key parity between the two files.

```bash
python3 check.py
```

---

## 🗂️ Project Structure

```text
clashbot/
├── cogs/                        # Modular bot commands
│   ├── achievements.py          # Badge system
│   ├── activity.py              # Activity score and kick list
│   ├── auth.py                  # Authorization (the global check lives here)
│   ├── battle_history.py        # Battle history analysis
│   ├── channel_manager.py       # Notification channel management
│   ├── deck_suggest.py          # Meta deck suggester
│   ├── donations.py             # Donation tracking
│   ├── prediction.py            # War result prediction
│   ├── profile.py               # Player profile analysis
│   ├── promotion.py             # Promotion suggestions
│   ├── records.py               # Clan records
│   ├── scraper.py               # RoyaleAPI / RCM web scraping (experimental)
│   ├── settings.py              # Server settings & language
│   ├── stats.py                 # matplotlib chart and table
│   ├── tracker.py               # Change tracking & member join/leave
│   ├── war.py                   # War commands, member tags, reminders
│   └── weekly_report.py         # Weekly report
├── data/                        # Auto-created on first run (in .gitignore)
│   ├── clashbot.db              # Main SQLite database
│   ├── authorized_users.json    # Authorized user list
│   ├── channel_config.json      # Channel configuration (bot-wide, not per-guild)
│   ├── clan_records.json        # Clan records
│   └── linked_accounts.json     # Discord ↔ CR account mapping
├── utils/                       # Utility modules
│   ├── channels.py              # Channel management module
│   ├── config.py                # .env reading and settings
│   ├── cr_api.py                # Clash Royale API client
│   ├── database.py              # SQLite wrapper
│   └── i18n.py                  # Multi-language engine
├── locales/                     # Language files
│   ├── en.json
│   └── tr.json
├── main.py                      # Bot entry point
├── check.py                     # Locale key parity checker
├── requirements.txt
├── .env.example
└── .env                         # Not committed to git
```

---

## ⏱️ Automated Tasks

| Task | Frequency | Description |
| --- | --- | --- |
| Change tracking | 10 min | Detects donation/war changes |
| Member join/leave | 2 min | Reports joined/left/kicked members |
| War reminder | 30 min | Deck warning near end of the war |
| Batched report | 60 min | Sends accumulated changes as a single embed |
| Periodic clan report | 2 hours | Clan status summary |
| Activity score | 6 hours | Saves all members' scores to the database |
| Badge check | 6 hours | Checks for newly earned badges |
| Weekly report | Mon 08:00 (UTC) | Automatic performance report |

---

## 🗄️ Database

The bot uses `aiosqlite` for data integrity and non-blocking async I/O. The database (`data/clashbot.db`) is created automatically on first run.

| Table | Contents |
| --- | --- |
| `players` | Player snapshot data (trophies, level, donations, etc.) |
| `donation_history` / `war_history` | Weekly performance records |
| `activity_log` | Daily activity score (for time-series analysis) |
| `trophy_snapshots` | Daily trophy snapshot |
| `achievements` | Earned badges *(created lazily by the `achievements.py` cog on first use, not part of the central schema)* |
| `server_settings` | Per-guild settings (e.g. preferred language) |

---

## 🛡️ Security

- **SQL injection protection:** Allowed column names in database queries are checked against a whitelist.
- **Role-based authorization:** Leader permission is verified via the Discord role ID rather than text-based role names (spoofing protection).
- **Concurrency safety:** JSON file operations are protected with `asyncio.Lock` / `threading.Lock`.
- **API token security:** Sensitive values live in `.env` and are excluded from version control via `.gitignore`.

---

## ⚠️ Known Limitations

Worth knowing before you self-host this bot:

- **Bot-wide, not per-guild, channel configuration:** `channel_config.json` is scoped to the bot process, not to individual servers. If the bot is added to multiple Discord servers, channel assignments are shared (and overwritten) across all of them.
- **`scraper.py` is experimental:** it depends on the HTML/internal structure of third-party sites like RoyaleAPI and RoyaleClanManager and can break without warning whenever those sites change. On failure it degrades gracefully — the bot doesn't crash, the affected command just returns no data.
- **No test infrastructure:** there's no unit test suite or CI pipeline in the repo; `check.py` only verifies key parity between locale files.
- **Locked by default:** as described in [Authorization Model](#-authorization-model), no command — including read-only ones — works until `LEADER_ROLE_ID` is set correctly or the user has Administrator permission.

---

## 🤝 Contributing

1. Fork the repo.
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -m 'feat: added new feature'`
4. Push your branch: `git push origin feature/new-feature`
5. Open a Pull Request.

---

<div align="center">

📄 License: [MIT](LICENSE)

</div>
