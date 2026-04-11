# Walkthrough: Internationalization (i18n) & English Refactoring

This document explains the planned architecture and execution strategy for translating the Clashbot codebase from Turkish to English and implementing a multi-language support system (i18n).

## 1. The Goal
The current codebase has Turkish variable names, file names, comments, and user-facing text. To make the project maintainable and usable globally, we need to:
1.  **Code Standardization:** Convert all underlying code (variables, files, functions, comments) strictly to English.
2.  **i18n (Internationalization):** Abstract all user-facing text (bot messages, embeds, error messages) into JSON files so the bot can support both English and Turkish dynamically based on the Discord server's preference.

## 2. Architecture of the i18n System

### Directory Structure
```text
clashbot/
├── locales/
│   ├── en.json       # English translations (Default)
│   └── tr.json       # Turkish translations
├── utils/
│   └── i18n.py       # Translation helper logic
```

### The JSON Approach
All strings will be moved to JSON files. For example, `locales/en.json`:
```json
{
  "commands": {
    "clan_info": "Clan Information",
    "player_not_found": "Player {tag} could not be found."
  },
  "war": {
    "status_title": "Current River Race Status",
    "no_participation": "Members with 0 medals"
  }
}
```

### The `i18n.py` Helper
A utility module will be created to load these JSON files into memory and provide a simple `get(guild_id, key, **kwargs)` function.
```python
# Pseudo-code for utils/i18n.py
def get(guild_id: int, key: str, **kwargs) -> str:
    lang = get_guild_language_from_db(guild_id) # Returns 'en' or 'tr'
    text = translations[lang].get(key, translations["en"][key])
    return text.format(**kwargs)
```

## 3. Refactoring Strategy

When handing this over to another developer, the work should be done in this specific order to prevent breaking the bot:

### Phase 1: Database & Core Utilities
1.  Add a `server_settings` table to [database.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/utils/database.py) to store `guild_id` and `language` (default 'en').
2.  Rename all files (`komutlar.txt` -> `commands.txt`, `kupa_data.json` -> `trophy_data.json`).
3.  Create the `utils/i18n.py` module and the `locales/` directory.

### Phase 2: Code Translation (Search & Replace)
1.  Translate all variable and function names in `utils/` (e.g., `savas_gecmisi` -> `war_history`).
2.  Translate all variable and function names in `cogs/`.
3.  Translate all Python docstrings and comments to English.

### Phase 3: Moving Strings to Locales
This is the most time-consuming part. The developer must go through every `ctx.send()`, `discord.Embed()`, and `logging.info()` call in the `cogs/` directory:
1.  Extract the Turkish string.
2.  Add an English translation to `en.json` and the original Turkish to `tr.json`.
3.  Replace the string in the Python code with `i18n.get(ctx.guild.id, "key")`.

### Phase 4: Command Names & Aliases
Change the core `discord.ext.commands` command names to English, but keep the Turkish versions as aliases so existing users aren't confused.
```python
@commands.command(name="clan", aliases=["klan", "c"])
async def clan(self, ctx): ...
```

## 4. Final Output
At the end of this process, the `/clashbot-global` repository will be fully compliant with global open-source standards. A developer from any country will be able to read the code, and a Discord server from any country will be able to set their language preference using `!language en` or `!dil tr`.
