"""
Konfigürasyon modülü – .env dosyasından değerleri yükler.
"""
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CR_API_TOKEN: str = os.getenv("CR_API_KEY", "")
CLAN_TAG: str = os.getenv("CLAN_TAG", "")
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
LIDER_ROLE_ID: int = int(os.getenv("LIDER_ROLE_ID", "0"))


def encode_tag(tag: str) -> str:
    """Clash Royale tag'ini URL-safe formata çevirir: #ABC → %23ABC"""
    if not tag:
        return ""
    return tag.replace("#", "%23")


def clean_tag(tag: str) -> str:
    """Tag'den # işaretini kaldırıp büyük harfe çevirir (karşılaştırma için)."""
    return tag.replace("#", "").upper()