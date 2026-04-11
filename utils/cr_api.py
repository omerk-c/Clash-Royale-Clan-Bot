"""
Async Clash Royale API client – aiohttp based.
All HTTP calls are non-blocking; does not block the bot event loop.
"""
import aiohttp
import logging
from typing import Optional
from utils.config import CR_API_TOKEN, CLAN_TAG, encode_tag

log = logging.getLogger(__name__)

BASE_URL = "https://api.clashroyale.com/v1"


class ClashRoyaleAPI:
    """Manages all API calls through a single aiohttp session."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazy session creation – opens on first call."""
        if self._session is None or self._session.closed:
            if not CR_API_TOKEN:
                log.error("CR_API_TOKEN is empty! Check the .env file.")

            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {CR_API_TOKEN}"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        """Clean up the session when the bot shuts down."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Common GET helper ──────────────────────────────────────────────
    async def _get(self, endpoint: str) -> Optional[dict]:
        session = await self._ensure_session()
        url = f"{BASE_URL}{endpoint}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    log.debug("API success: %s", url)
                    return data
                elif resp.status == 403:
                    log.error(
                        "API 403 Forbidden - Invalid token or IP not whitelisted: %s",
                        url,
                    )
                elif resp.status == 404:
                    log.warning("API 404 Not Found: %s", url)
                else:
                    log.warning("API %s → HTTP %s", url, resp.status)
        except aiohttp.ClientError as exc:
            log.error("API request failed: %s – %s", url, exc)
        return None

    # ── Public methods ───────────────────────────────────────────────
    async def get_clan_info(self) -> Optional[dict]:
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}")

    async def get_clan_members(self) -> list[dict]:
        clan = await self.get_clan_info()
        if clan and "memberList" in clan:
            return clan["memberList"]
        return []

    async def get_current_river_race(self) -> Optional[dict]:
        """Returns active river race data."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/currentriverrace")

    # ── Player Profile ─────────────────────────────────────────────────
    async def get_player_info(self, player_tag: str) -> Optional[dict]:
        """Returns individual player profile."""
        return await self._get(f"/players/{encode_tag(player_tag)}")

    async def get_player_battle_log(self, player_tag: str) -> Optional[list]:
        """Returns the player's last 25 battle history."""
        return await self._get(f"/players/{encode_tag(player_tag)}/battlelog")

    async def get_player_upcoming_chests(self, player_tag: str) -> Optional[dict]:
        """Returns the player's upcoming chests."""
        return await self._get(f"/players/{encode_tag(player_tag)}/upcomingchests")

    # ── River Race Log (CW2) ──────────────────────────────────────────
    async def get_river_race_log(self) -> Optional[dict]:
        """Returns the clan's river race history (Clan Wars 2)."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/riverracelog")

    async def get_river_race_log_for(self, tag: str) -> Optional[dict]:
        """Returns any clan's river race history."""
        return await self._get(f"/clans/{encode_tag(tag)}/riverracelog")

    # ── Clan Info (Any Clan) ──────────────────────────────────────────
    async def get_clan_info_for(self, tag: str) -> Optional[dict]:
        """Returns any clan's information."""
        return await self._get(f"/clans/{encode_tag(tag)}")

    # ── Legacy Warlog (CW1 – backward compatibility) ────────────────────
    async def get_clan_war_log(self) -> Optional[dict]:
        """Legacy CW1 warlog. Use /riverracelog for CW2 clans."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/warlog")

    async def get_war_log_for(self, tag: str) -> Optional[dict]:
        """Any clan's legacy CW1 war history."""
        return await self._get(f"/clans/{encode_tag(tag)}/warlog")