"""
Clash Royale Clan Bot – Main entry point.
All business logic is in Cogs; this file just starts the bot.
"""
import logging

import discord
from discord.ext import commands

from utils.config import DISCORD_TOKEN, CHANNEL_ID
from utils.cr_api import ClashRoyaleAPI
from utils.database import Database
import utils.i18n as i18n

# ── Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("clashbot")

# ── Bot setup ──────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Async API client and database
bot.cr_api = ClashRoyaleAPI()
bot.db = Database()

# ── Cog loading ──────────────────────────────────────────────────

EXTENSIONS = [
    "cogs.war",
    "cogs.donations",
    "cogs.tracker",
    "cogs.prediction",
    "cogs.stats",
    "cogs.auth",
    "cogs.activity",
    "cogs.profile",
    "cogs.weekly_report",
    "cogs.promotion",
    "cogs.achievements",
    "cogs.battle_history",
    "cogs.deck_suggest",
    "cogs.records",
    "cogs.channel_manager",
    "cogs.settings",
]


@bot.event
async def setup_hook() -> None:
    """Load database and Cogs before bot starts."""
    await bot.db.connect()
    log.info("Database initialized.")

    # Load guild settings and add to i18n cache
    guild_settings = await bot.db.get_all_guild_settings()
    for setting in guild_settings:
        i18n.set_guild_language(int(setting["guild_id"]), setting["language"])
    log.info("%d guild settings loaded.", len(guild_settings))

    for ext in EXTENSIONS:
        try:
            await bot.load_extension(ext)
            log.info("Cog loaded: %s", ext)
        except Exception:
            log.exception("Failed to load Cog: %s", ext)


async def on_bot_shutdown():
    await bot.cr_api.close()
    await bot.db.close()
    log.info("API session and database closed.")


original_close = bot.close


async def close():
    await on_bot_shutdown()
    await original_close()


bot.close = close


@bot.event
async def on_ready() -> None:
    log.info("Bot online: %s (ID: %s)", bot.user, bot.user.id)
    log.info("Notification channel: %s", CHANNEL_ID)


# ── Start ────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)