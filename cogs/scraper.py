"""
Scraper Cog – Extra clan stats via RoyaleAPI web scraping.
Uses aiohttp + BeautifulSoup4. Graceful fallback against Cloudflare protection.

Provides /royaleapi as a slash command, and can also be called by
other cogs via the scrape_clan_extras() method.
"""
import re
import json
import logging

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands

from utils.config import CLAN_TAG, encode_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)

# Standard browser User-Agent to bypass basic Cloudflare checks
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

class ScraperCog(commands.Cog, name="Scraper"):
    """Extra statistics using RoyaleAPI web scraping."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def scrape_clan_extras(self, clan_tag: str) -> dict[str, str] | None:
        """
        Scrapes the clan page from RoyaleAPI for extra stats.
        Can be called by other cogs (like prediction.py).
        Returns None on failure (graceful fallback).
        """
        clean_tag = clan_tag.replace("#", "")
        url = f"https://royaleapi.com/clan/{clean_tag}"

        try:
            async with aiohttp.ClientSession(
                headers=BROWSER_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as session:
                async with session.get(url) as resp:
                    if resp.status in (403, 503):
                        log.warning(
                            "RoyaleAPI access blocked: HTTP %s – Cloudflare might be active",
                            resp.status,
                        )
                        return None

                    if resp.status != 200:
                        log.warning("RoyaleAPI HTTP %s", resp.status)
                        return None

                    html = await resp.text()

        except aiohttp.ClientError as exc:
            log.error("RoyaleAPI connection error: %s", exc)
            return None

        # ── HTML parse – BeautifulSoup4 ───────────────────────────────
        soup = BeautifulSoup(html, "html.parser")
        results: dict[str, str] = {}

        try:
            # Clan Name
            name_elem = soup.select_one("h1.header__name, .clan__name, h1, .clan-name")
            if name_elem:
                results["Clan"] = name_elem.get_text(strip=True)

            # Look for stat cards
            stat_items = soup.select(".stat__container, .clan_stats .stat, .ui__card, .stat-item")
            for item in stat_items:
                label_elem = item.select_one(".stat_title, .stat__label, .ui__headerSmall, .label")
                value_elem = item.select_one(".stat_value, .stat__value, .ui__headerMedium, .value")
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    for keyword in ("rank", "trophies", "donations", "war", "score", "members", "level"):
                        if keyword.lower() in label.lower():
                            results[label] = value
                            break

            # Alternative approach: Iterate over elements with class containing 'stat'
            if not results:
                stats = soup.select("[class*='stat'], [class*='Stat']")
                for stat in stats:
                    elements = stat.find_all(["span", "div", "p"], recursive=False)
                    if len(elements) >= 2:
                        label = elements[0].get_text(strip=True)
                        value = elements[1].get_text(strip=True)
                        for keyword in ("rank", "trophies", "donations", "war", "score", "members", "level"):
                            if keyword.lower() in label.lower():
                                results[label] = value
                                break

        except Exception as exc:
            log.warning("RoyaleAPI HTML parse error: %s", exc)
            return None

        return results if results else None

    # ── RoyaleClanManager (RCM) Scraping ───────────────────────────

    async def scrape_rcm_war_history(self, clan_tag: str) -> list[int]:
        """
        Scrapes the last 10 weeks of fame history from RoyaleClanManager.
        Mimics Next.js RSC (Server Action) request.
        """
        clean_tag = clan_tag.replace("#", "").upper()
        url = f"https://royaleclanmanager.com/war-stats?clan-tag={clean_tag}"
        
        headers = {
            "User-Agent": BROWSER_HEADERS["User-Agent"],
            "accept": "text/x-component",
            "content-type": "text/plain;charset=UTF-8",
            "next-action": "7cd2182b7fce9bf8072314754288990c4d1557b3",
            "next-router-state-tree": f'["", {{"children": ["war-stats", {{"children": ["__PAGE__", {{}}, "/war-stats?clan-tag={clean_tag}", "refresh"]}}]}}, null, null, true]'
        }
        body = json.dumps([clean_tag])

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=body, timeout=15) as resp:
                    if resp.status != 200:
                        log.warning("RCM war history HTTP %s", resp.status)
                        return []
                    text = await resp.text()

            matches = re.findall(r'\[(\d{4,6}(?:,\d{4,6}){2,})\]', text)
            for m in matches:
                nums = [int(n) for n in m.split(",")]
                if 5 <= len(nums) <= 12:
                    return nums
            
            return []

        except Exception as e:
            log.error("RCM war history scraping error: %s", e)
            return []

    async def scrape_rcm_member_history(self, clan_tag: str) -> dict[str, list[int]]:
        """
        Scrapes player-based 10 weeks of history from RoyaleClanManager.
        Mimics Next.js RSC (Server Action) request.
        """
        clean_tag = clan_tag.replace("#", "").upper()
        url = f"https://royaleclanmanager.com/clan-table?clan-tag={clean_tag}"
        
        headers = {
            "User-Agent": BROWSER_HEADERS["User-Agent"],
            "accept": "text/x-component",
            "content-type": "text/plain;charset=UTF-8",
            "next-action": "2350a68acd3c07188dbb2946ed3c8a4b3fcf8c1c",
            "next-router-state-tree": f'["", {{"children": ["clan-table", {{"children": ["__PAGE__", {{}}, "/clan-table?clan-tag={clean_tag}", "refresh"]}}]}}, null, null, true]'
        }
        body = json.dumps([clean_tag])

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=body, timeout=15) as resp:
                    if resp.status != 200:
                        log.warning("RCM member history HTTP %s", resp.status)
                        return {}
                    text = await resp.text()

            results = {}
            pattern = r'(?:\\?"Name\\?":\\?"(.*?)\\?".*?\\?"War Points\\?":\[(.*?)\])'
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1)
                points_str = match.group(2)
                try:
                    points = [int(p.strip()) for p in points_str.split(",") if p.strip().isdigit()]
                    if points:
                        results[name] = points
                except:
                    continue
            
            return results

        except Exception as e:
            log.error("RCM member history scraping error: %s", e)
            return {}

    # ── !royaleapi command ─────────────────────────────────────────────

    @commands.command(name="royaleapi")
    async def royaleapi_cmd(self, ctx: commands.Context, clan_tag: str = None) -> None:
        """Fetches extra clan stats from RoyaleAPI (!royaleapi or !royaleapi #TAG)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        msg = await ctx.send(t("scraper.fetching"))

        tag = clan_tag or CLAN_TAG
        if not tag.startswith("#"):
            tag = f"#{tag}"

        extras = await self.scrape_clan_extras(tag)

        if not extras:
            await msg.edit(content=t("scraper.fetch_error"))
            return

        embed = discord.Embed(
            title=t("scraper.title", clan=extras.get('Clan', tag)),
            description=t("scraper.desc"),
            color=0x00CED1,
        )

        priority_fields = ["Level", "Members", "Trophies", "War", "Rank", "Score"]
        
        for field in priority_fields:
            for key, value in extras.items():
                if field.lower() in key.lower():
                    embed.add_field(name=key, value=value, inline=True)
                    break
        
        for key, value in extras.items():
            added = any(field.name == key for field in embed.fields)
            if not added and key != "Clan":
                embed.add_field(name=key, value=value, inline=True)

        embed.set_footer(text=t("scraper.footer"))
        await msg.delete()
        await ctx.send(embed=embed)

    @commands.command(name="rcm_test")
    async def rcm_test_cmd(self, ctx: commands.Context) -> None:
        """RCM scraping debug command."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        msg = await ctx.send(t("scraper.rcm_testing"))
        history = await self.scrape_rcm_war_history(CLAN_TAG)
        members = await self.scrape_rcm_member_history(CLAN_TAG)
        
        out = t("scraper.rcm_history", history=history)
        out += t("scraper.rcm_members", count=len(members))
        if members:
            first_name = list(members.keys())[0]
            out += t("scraper.rcm_sample", name=first_name, sample=members[first_name])
            
        await msg.edit(content=out)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScraperCog(bot))