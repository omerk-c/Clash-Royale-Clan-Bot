# Clashbot i18n & English Refactoring

## Phase 1 – Core Infrastructure
- [ ] Create `utils/i18n.py` (load locales, `get()`, guild language cache)
- [ ] Create `locales/en.json` with all ~350 user-facing strings
- [ ] Create `locales/tr.json` mirroring `en.json`
- [ ] Add `server_settings` table to [database.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/utils/database.py)
- [ ] Add `!language`/`!dil` command for guild admins

## Phase 2 – Code Translation (Turkish → English)
- [ ] Rename all 15 Cog `name=` parameters to English
- [ ] Rename all 33+ command names to English (keep TR aliases)
- [ ] Rename Turkish variables/functions across all cogs and utils
- [ ] Translate all docstrings and comments to English
- [ ] Migrate achievement badge IDs (DB migration in `_ensure_table`)

## Phase 3 – Wire Strings Through i18n
- [ ] Refactor [war.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/war.py) (~40 strings)
- [ ] Refactor [tracker.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/tracker.py) (~15 strings)
- [ ] Refactor [donations.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/donations.py) (~10 strings)
- [ ] Refactor [stats.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/stats.py) (~15 strings)
- [ ] Refactor [prediction.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/prediction.py) (~10 strings)
- [ ] Refactor [activity.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/activity.py) (~20 strings)
- [ ] Refactor [auth.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/auth.py) (~10 strings)
- [ ] Refactor [profile.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/profile.py) (~25 strings)
- [ ] Refactor [promotion.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/promotion.py) (~15 strings)
- [ ] Refactor [achievements.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/achievements.py) (~20 strings)
- [ ] Refactor [battle_history.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/battle_history.py) (~20 strings)
- [ ] Refactor [deck_suggest.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/deck_suggest.py) (~15 strings)
- [ ] Refactor [records.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/records.py) (~20 strings)
- [ ] Refactor [scraper.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/scraper.py) (~10 strings)
- [ ] Refactor [channel_manager.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/channel_manager.py) (~15 strings)
- [ ] Refactor [weekly_report.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/weekly_report.py) (~15 strings)

## Phase 4 – Documentation & Cleanup
- [ ] Rewrite [README.md](file:///home/kayra/Masaüstü/clashbot-global/clashbot/README.md) in English with i18n section
- [ ] Update [main.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/main.py) for i18n initialization
- [ ] Verification: syntax check, JSON validity, key parity
