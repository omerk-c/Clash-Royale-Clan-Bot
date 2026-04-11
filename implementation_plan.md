# Clashbot i18n & English Refactoring – Implementation Plan

## Goal

Refactor the entire Clashbot codebase so that **all code** (variables, functions, classes, comments, docstrings, filenames) is in English, and **all user-facing text** is served through a JSON-based i18n system supporting English (default) and Turkish.

> [!IMPORTANT]
> The execution order below is critical. Each phase depends on the previous one. Do **not** skip phases.

---

## Phase 1 – Core Infrastructure

### [NEW] [i18n.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/utils/i18n.py)

Create the i18n engine with these responsibilities:
- Load `locales/en.json` and `locales/tr.json` into memory at import time
- Expose `get(guild_id, key, **kwargs) -> str` for dot-notation lookups (e.g. `"war.title"`)
- Expose `set_guild_language(guild_id, lang)` and `get_guild_language(guild_id) -> str`
- Store per-guild language in an in-memory dict, backed by DB (loaded on startup)
- Fallback chain: requested lang → `"en"` → raw key

### [NEW] [en.json](file:///home/kayra/Masaüstü/clashbot-global/clashbot/locales/en.json)

All user-facing strings organized into top-level sections:
- `"common"` – shared phrases (errors, confirmations, Unknown, etc.)
- `"war"`, `"tracker"`, `"donations"`, `"stats"`, `"prediction"`, `"activity"`, `"profile"`, `"promotion"`, `"achievements"`, `"battle_history"`, `"deck"`, `"records"`, `"scraper"`, `"channels"`, `"weekly"`, `"auth"`, `"help"` – one section per cog

### [NEW] [tr.json](file:///home/kayra/Masaüstü/clashbot-global/clashbot/locales/tr.json)

Mirror of `en.json` with all original Turkish strings.

### [MODIFY] [database.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/utils/database.py)

- Add `server_settings` table: `(guild_id TEXT PRIMARY KEY, language TEXT DEFAULT 'en')`
- Add methods: `get_guild_language(guild_id)`, `set_guild_language(guild_id, lang)`
- On startup, load all guild prefs into `i18n` module's cache

### [NEW] `!language` / `!dil` command

Add a small command (in [cogs/channel_manager.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/channel_manager.py) or a new `cogs/settings.py`) to let admins switch guild language between `en` and `tr`.

---

## Phase 2 – Code Translation (English variable/function/class/comment names)

> [!NOTE]
> File names stay the same (already English). Only internal identifiers change.

### Cog name mapping (class `name=` parameter)

| Old Turkish | New English |
|---|---|
| `name="Savaş"` | `name="War"` |
| `name="Takip"` | `name="Tracker"` |
| `name="Bağışlar"` | `name="Donations"` |
| `name="İstatistikler"` | `name="Statistics"` |
| `name="Tahmin"` | `name="Prediction"` |
| `name="Aktivite"` | `name="Activity"` |
| `name="Yetki"` | `name="Auth"` |
| `name="Profil"` | `name="Profile"` |
| `name="Terfi"` | `name="Promotion"` |
| `name="Başarılar"` | `name="Achievements"` |
| `name="Savaş Geçmişi"` | `name="Battle History"` |
| `name="Deste Önerici"` | `name="Deck Suggest"` |
| `name="Rekorlar"` | `name="Records"` |
| `name="Kanal Yönetimi"` | `name="Channel Manager"` |
| `name="Haftalık Rapor"` | `name="Weekly Report"` |

### Command name mapping (keep Turkish as aliases)

| Old name | New name | Aliases (old Turkish kept) |
|---|---|---|
| `klan` | `clan` | `klan` |
| `savaslar` | `wars` | `savaslar` |
| `katki` | `contribution` | `katki` |
| `katilmayanlar` | `nonparticipants` | `katilmayanlar`, `sıfırcılar` |
| `liste` | `members` | `liste` |
| `yardim` | `help` | `yardim`, `yardım` |
| `bagis` | `donations` | `bagis` |
| `somuruculer` | `leechers` | `somuruculer`, `sömürücüler` |
| `grafik` | `chart` | `grafik` |
| `oyuncu_tablo` | `player_table` | `oyuncu_tablo` |
| `tahmin` | `predict` | `tahmin` |
| `aktivite` | `activity` | `aktivite` |
| `kicklist` | `kicklist` | *(already English)* |
| `profil` | `profile` | `profil` |
| `terfi` | `promote` | `terfi` |
| `terfi_gecmis` | `promote_history` | `terfi_gecmis`, `terfi_geçmiş` |
| `rozetlerim` | `my_badges` | `rozetlerim` |
| `rozet_siralamasi` | `badge_leaderboard` | `rozet_siralamasi`, `rozet_sıralaması` |
| `rozetler` | `badges` | `rozetler` |
| `savas_gecmisi` | `battle_history` | `savas_gecmisi`, `savaş_geçmişi` |
| `deste_analiz` | `deck_analysis` | `deste_analiz` |
| `deste` | `deck` | `deste` |
| `deste_oner` | `deck_suggest` | `deste_oner`, `deste_öner` |
| `deste_rastgele` | `random_deck` | `deste_rastgele` |
| `meta` | `meta` | *(already English)* |
| `rekorlar` | `records` | `rekorlar` |
| `rekor_gecmis` | `record_history` | `rekor_gecmis`, `rekor_geçmiş` |
| `rekor_sifirla` | `record_reset` | `rekor_sifirla` |
| `haftalik` | `weekly` | `haftalik`, `haftalık` |
| `haftalik_ayar` | `weekly_settings` | `haftalik_ayar` |
| `kanal_ayar` | `channel_set` | `kanal_ayar` |
| `kanal_kaldir` | `channel_remove` | `kanal_kaldir`, `kanal_kaldır` |
| `kanal_liste` | `channel_list` | `kanal_liste` |
| `kanal_test` | `channel_test` | `kanal_test` |
| `yetki_ver` | `grant_auth` | `yetki_ver` |
| `yetki_al` | `revoke_auth` | `yetki_al` |
| `yetki_liste` | `auth_list` | `yetki_liste` |

### Key variable renames across files

- `_role_turkish()` → `_translate_role()` (in [profile.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/profile.py), [promotion.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/promotion.py), [war.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/war.py))
- `GAME_MODE_TR` → `GAME_MODE_NAMES` (in [battle_history.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/battle_history.py))
- `roles_tr` → `role_names` (in [war.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/war.py))
- `lazy_members` / `lazy_players` → `inactive_members` / `inactive_players`
- `ekstra_bilgi` → `extra_info`
- `kategori` → `category`
- All Turkish docstrings/comments → English equivalents

### Achievement badge IDs (internal keys)

| Old | New |
|---|---|
| `ilk_kan` | `first_blood` |
| `ates_serisi` | `fire_streak` |
| `bagis_krali` | `donation_king` |
| `sadik_asker` | `loyal_soldier` |
| `savas_makinesi` | `war_machine` |
| `comert_ruh` | `generous_soul` |
| `mukemmeliyetci` | `perfectionist` |
| `efsane` | `legend` |

> [!WARNING]
> Badge ID changes require a one-time DB migration (`UPDATE achievements SET badge_id = 'first_blood' WHERE badge_id = 'ilk_kan'` etc.). A migration helper should be added to the `_ensure_table` method in [achievements.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/cogs/achievements.py).

---

## Phase 3 – Extract Strings into Locale Files

For every cog, replace hardcoded Turkish strings in `ctx.send()`, `discord.Embed()`, `embed.add_field()`, `embed.set_footer()`, etc., with calls to `i18n.get(ctx.guild.id, "section.key", **vars)`.

**Pattern:**
```python
# BEFORE
await ctx.send("❌ Klan bilgisi alınamadı.")

# AFTER
await ctx.send(t("war.clan_info_failed"))
```

Where `t` is a shorthand bound at the top of each command:
```python
t = lambda key, **kw: i18n.get(ctx.guild.id, key, **kw)
```

Each cog file has between 10–40 unique user-facing strings. Total estimated: ~350 strings across 15 cog files.

---

## Phase 4 – Documentation & Cleanup

### [MODIFY] [README.md](file:///home/kayra/Masaüstü/clashbot-global/clashbot/README.md)

- Full English rewrite
- Add "Multi-language Support" section explaining `!language en|tr`
- Update command table with new English names

### [MODIFY] [main.py](file:///home/kayra/Masaüstü/clashbot-global/clashbot/main.py)

- Update cog loading to call `i18n.load()` on startup
- Add guild language cache initialization from DB

---

## Verification Plan

### Automated
```bash
# 1. Syntax check – all files parse
python -m py_compile utils/i18n.py
python -m py_compile utils/database.py
find cogs/ -name "*.py" -exec python -m py_compile {} \;

# 2. JSON validity
python -c "import json; json.load(open('locales/en.json')); json.load(open('locales/tr.json'))"

# 3. Key parity – every key in en.json exists in tr.json
python -c "
import json
en = json.load(open('locales/en.json'))
tr = json.load(open('locales/tr.json'))
def keys(d, prefix=''):
    r = set()
    for k, v in d.items():
        full = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            r |= keys(v, full)
        else:
            r.add(full)
    return r
missing = keys(en) - keys(tr)
assert not missing, f'Missing TR keys: {missing}'
print('All keys match!')
"
```

### Manual
- Run the bot, execute every command in both `en` and `tr` mode to confirm output
