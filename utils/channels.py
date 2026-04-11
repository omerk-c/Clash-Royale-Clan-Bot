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

# ── Eşzamanlılık koruması ──────────────────────────────────────────
_config_lock = threading.Lock()

# ── Kanal Kategorileri ──────────────────────────────────────────────

CHANNEL_TYPES = {
    "main": {
        "emoji": "📢",
        "name": "Ana Kanal",
        "description": "Genel bildirimler ve varsayılan kanal",
    },
    "war": {
        "emoji": "⚔️",
        "name": "Savaş Bildirimleri",
        "description": "Savaş hatırlatıcı, katılmayanlar, savaş durumu",
    },
    "badges": {
        "emoji": "🏅",
        "name": "Rozet Bildirimleri",
        "description": "Yeni kazanılan rozetler ve başarı duyuruları",
    },
    "records": {
        "emoji": "🏆",
        "name": "Rekor Bildirimleri",
        "description": "Yeni rekor kırılma duyuruları",
    },
    "members": {
        "emoji": "👥",
        "name": "Üye Hareketleri",
        "description": "Üye giriş/çıkış bildirimleri",
    },
    "reports": {
        "emoji": "📊",
        "name": "Raporlar",
        "description": "Haftalık rapor, periyodik klan özeti",
    },
    "activity": {
        "emoji": "📈",
        "name": "Aktivite Takibi",
        "description": "Saatlik aktivite özeti, bağış/savaş değişimleri",
    },
}


def _load_channel_config() -> dict:
    """Kanal yapılandırmasını JSON'dan yükler."""
    with _config_lock:
        try:
            with open(CHANNEL_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


def _save_channel_config(config: dict) -> None:
    """Kanal yapılandırmasını JSON'a kaydeder."""
    with _config_lock:
        os.makedirs(os.path.dirname(CHANNEL_CONFIG_PATH), exist_ok=True)
        with open(CHANNEL_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)


def set_channel(channel_type: str, channel_id: int) -> bool:
    """
    Belirli bir bildirim türü için kanal atar.
    Returns: True ise başarılı.
    """
    if channel_type not in CHANNEL_TYPES:
        return False

    config = _load_channel_config()
    config[channel_type] = channel_id
    _save_channel_config(config)
    return True


def remove_channel(channel_type: str) -> bool:
    """
    Belirli bir bildirim türü için kanal atamasını kaldırır.
    Varsayılan (main) kanala düşer.
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
    Belirli bir bildirim türü için kanal ID'si döndürür.
    Atanmamışsa varsayılan (main) kanalını, o da yoksa default_channel_id'yi döndürür.
    """
    config = _load_channel_config()

    # Önce istenen türün kanalını kontrol et
    channel_id = config.get(channel_type)
    if channel_id:
        return int(channel_id)

    # Yoksa main kanalını kontrol et
    main_id = config.get("main")
    if main_id:
        return int(main_id)

    # Hiçbiri yoksa .env'deki varsayılanı kullan
    return default_channel_id


def get_all_channels() -> dict[str, Optional[int]]:
    """Tüm kanal atamalarını döndürür."""
    config = _load_channel_config()
    result = {}
    for channel_type in CHANNEL_TYPES:
        result[channel_type] = config.get(channel_type)
    return result


async def get_notification_channel(
    bot: commands.Bot, channel_type: str, default_channel_id: int
) -> Optional[discord.TextChannel]:
    """
    Bot üzerinden bildirim kanalını döndürür.
    Kanal bulunamazsa None döner.
    """
    cid = get_channel_id(channel_type, default_channel_id)
    channel = bot.get_channel(cid)
    if channel is None:
        # Fallback: varsayılan kanal
        channel = bot.get_channel(default_channel_id)
    return channel