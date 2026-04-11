"""
Asenkron Clash Royale API istemcisi – aiohttp tabanlı.
Tüm HTTP çağrıları non-blocking; bot event loop'u bloklamaz.
"""
import aiohttp
import logging
from typing import Optional
from utils.config import CR_API_TOKEN, CLAN_TAG, encode_tag

log = logging.getLogger(__name__)

BASE_URL = "https://api.clashroyale.com/v1"


class ClashRoyaleAPI:
    """Tek bir aiohttp session üzerinden tüm API çağrılarını yönetir."""

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Lazy session oluşturma – ilk çağrıda açılır."""
        if self._session is None or self._session.closed:
            if not CR_API_TOKEN:
                log.error("CR_API_TOKEN boş! .env dosyasını kontrol edin.")

            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {CR_API_TOKEN}"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        """Bot kapanırken session'ı temizle."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Ortak GET helper ──────────────────────────────────────────────
    async def _get(self, endpoint: str) -> Optional[dict]:
        session = await self._ensure_session()
        url = f"{BASE_URL}{endpoint}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    log.debug("API başarılı: %s", url)
                    return data
                elif resp.status == 403:
                    log.error(
                        "API 403 Forbidden - Token geçersiz veya IP whitelisted değil: %s",
                        url,
                    )
                elif resp.status == 404:
                    log.warning("API 404 Not Found: %s", url)
                else:
                    log.warning("API %s → HTTP %s", url, resp.status)
        except aiohttp.ClientError as exc:
            log.error("API isteği başarısız: %s – %s", url, exc)
        return None

    # ── Public metotlar ───────────────────────────────────────────────
    async def get_clan_info(self) -> Optional[dict]:
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}")

    async def get_clan_members(self) -> list[dict]:
        clan = await self.get_clan_info()
        if clan and "memberList" in clan:
            return clan["memberList"]
        return []

    async def get_current_river_race(self) -> Optional[dict]:
        """Aktif nehir yarışı verisini döndürür."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/currentriverrace")

    # ── Oyuncu Profili ─────────────────────────────────────────────────
    async def get_player_info(self, player_tag: str) -> Optional[dict]:
        """Bireysel oyuncu profili döndürür."""
        return await self._get(f"/players/{encode_tag(player_tag)}")

    async def get_player_battle_log(self, player_tag: str) -> Optional[list]:
        """Oyuncunun son 25 savaş geçmişini döndürür."""
        return await self._get(f"/players/{encode_tag(player_tag)}/battlelog")

    async def get_player_upcoming_chests(self, player_tag: str) -> Optional[dict]:
        """Oyuncunun gelecek sandıklarını döndürür."""
        return await self._get(f"/players/{encode_tag(player_tag)}/upcomingchests")

    # ── River Race Log (CW2) ──────────────────────────────────────────
    async def get_river_race_log(self) -> Optional[dict]:
        """Klanın nehir yarışı geçmişini döndürür (Clan Wars 2)."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/riverracelog")

    async def get_river_race_log_for(self, tag: str) -> Optional[dict]:
        """Herhangi bir klanın nehir yarışı geçmişini döndürür."""
        return await self._get(f"/clans/{encode_tag(tag)}/riverracelog")

    # ── Klan Bilgisi (Herhangi Bir Klan) ──────────────────────────────
    async def get_clan_info_for(self, tag: str) -> Optional[dict]:
        """Herhangi bir klanın bilgilerini döndürür."""
        return await self._get(f"/clans/{encode_tag(tag)}")

    # ── Eski Warlog (CW1 – geriye dönük uyumluluk) ────────────────────
    async def get_clan_war_log(self) -> Optional[dict]:
        """Eski CW1 warlog. CW2 klanları için /riverracelog kullanın."""
        return await self._get(f"/clans/{encode_tag(CLAN_TAG)}/warlog")

    async def get_war_log_for(self, tag: str) -> Optional[dict]:
        """Herhangi bir klanın eski CW1 savaş geçmişi."""
        return await self._get(f"/clans/{encode_tag(tag)}/warlog")