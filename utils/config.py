"""
Configuration module – loads values from .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CR_API_TOKEN: str = os.getenv("CR_API_KEY", "")
CLAN_TAG: str = os.getenv("CLAN_TAG", "")
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))
LEADER_ROLE_ID: int = int(os.getenv("LEADER_ROLE_ID", "0"))

def encode_tag(tag: str) -> str:
    """Convert Clash Royale tag to URL-safe format: #ABC → %23ABC"""
    if not tag:
        return ""
    return tag.replace("#", "%23")


def clean_tag(tag: str) -> str:
    """Remove # from tag and convert to uppercase for comparison."""
    return tag.replace("#", "").upper()