import json
import logging
import os
import threading
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

CHANNEL_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "channel_config.json"
)

# ── Concurrency protection ──────────────────────────────────────────
_config_lock = threading.Lock()

# ── Channel Categories ──────────────────────────────────────────────

CHANNEL_TYPES = {
    "main": {
        "emoji": "📢",
        "name": "Main Channel",
        "description": "General notifications and default channel",
    },
    "war": {
        "emoji": "⚔️",
        "name": "War Notifications",
        "description": "War reminders, non-participants, war status",
    },
    "badges": {
        "emoji": "🏅",
        "name": "Badge Notifications",
        "description": "Newly earned badges and achievement announcements",
    },
    "records": {
        "emoji": "🏆",
        "name": "Record Notifications",
        "description": "New record-breaking announcements",
    },
    "members": {
        "emoji": "👥",
        "name": "Member Activity",
        "description": "Member join/leave notifications",
    },
    "reports": {
        "emoji": "📊",
        "name": "Reports",
        "description": "Weekly report, periodic clan summary",
    },
    "activity": {
        "emoji": "📈",
        "name": "Activity Tracking",
        "description": "Hourly activity summary, donation/war changes",
    },
}


def _load_channel_config() -> dict:
    """Loads channel configuration from JSON."""
    with _config_lock:
        try:
            with open(CHANNEL_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


def _save_channel_config(config: dict) -> None:
    """Saves channel configuration to JSON."""
    with _config_lock:
        os.makedirs(os.path.dirname(CHANNEL_CONFIG_PATH), exist_ok=True)
        with open(CHANNEL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)


def set_channel(channel_type: str, channel_id: int) -> bool:
    """
    Assigns a channel for a specific notification type.
    Returns: True if successful.
    """
    if channel_type not in CHANNEL_TYPES:
        return False

    config = _load_channel_config()
    config[channel_type] = channel_id
    _save_channel_config(config)
    return True


def remove_channel(channel_type: str) -> bool:
    """
    Removes channel assignment for a specific notification type.
    Falls back to the default (main) channel.
    """
    if channel_type not in CHANNEL_TYPES:
        return False

    config = _load_channel_config()
    if channel_type in config:
        del config[channel_type]
        _save_channel_config(config)
    return True


def get_channel_id(channel_type: str, default_channel_id: int) -> int:
    """
    Returns the channel ID for a specific notification type.
    Falls back to the main channel if unassigned, then to default_channel_id.
    """
    config = _load_channel_config()

    # First check the requested type's channel
    channel_id = config.get(channel_type)
    if channel_id:
        return int(channel_id)

    # Otherwise check the main channel
    main_id = config.get("main")
    if main_id:
        return int(main_id)

    # If none found, use the default from .env
    return default_channel_id


def get_all_channels() -> dict[str, Optional[int]]:
    """Returns all channel assignments."""
    config = _load_channel_config()
    result = {}
    for channel_type in CHANNEL_TYPES:
        result[channel_type] = config.get(channel_type)
    return result


async def get_notification_channel(
    bot: commands.Bot, channel_type: str, default_channel_id: int
) -> Optional[discord.TextChannel]:
    """
    Returns the notification channel via the bot.
    Returns None if the channel is not found.
    """
    cid = get_channel_id(channel_type, default_channel_id)
    channel = bot.get_channel(cid)
    if channel is None:
        # Fallback: default channel
        channel = bot.get_channel(default_channel_id)
    return channel