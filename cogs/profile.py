"""
Profile Cog – Shows individual player profile using Clash Royale API /players/{tag} endpoint.

Commands:
  !profile #TAG     → Detailed player profile
  !profile @mention → Fetches automatically if Discord account is linked

Showcase Info:
  - Trophies & Best Trophies
  - Player Level (King Level)
  - Favorite Card
  - Win Rate (wins / (wins + losses))
  - Total Battles
  - Challenge Wins
  - Clan Donations
  - Tournament Cards Won
  - Active Clan & Role
"""
import json
import logging
import os
from typing import Optional

import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
from utils.config import encode_tag, clean_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)

LINKED_ACCOUNTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "linked_accounts.json"
)


def _load_linked_accounts() -> dict[str, str]:
    """Loads {cr_tag: discord_id} dict from linked_accounts.json."""
    try:
        with open(LINKED_ACCOUNTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _reverse_linked_accounts() -> dict[str, str]:
    """Reverse mapping: Discord ID → CR Tag."""
    linked = _load_linked_accounts()
    return {v: k for k, v in linked.items()}


def _arena_emoji(arena_name: str) -> str:
    """Returns emoji based on arena name."""
    arena_lower = arena_name.lower()
    if "legendary" in arena_lower or "efsanevi" in arena_lower:
        return "🏆"
    elif "champion" in arena_lower or "şampiyon" in arena_lower:
        return "👑"
    elif "master" in arena_lower or "usta" in arena_lower:
        return "⭐"
    elif "challenger" in arena_lower or "meydan" in arena_lower:
        return "🎯"
    return "🏟️"


class ProfileCog(commands.Cog, name="Profile"):
    """Individual player profile commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    async def _get_player_data(self, tag: str) -> Optional[dict]:
        """Fetches player data from API."""
        return await self.api._get(f"/players/{encode_tag(tag)}")

    @commands.command(name="profile", aliases=["profil"])
    async def profile_cmd(self, ctx: commands.Context, target: str = None) -> None:
        """
        Shows detailed player profile.

        Usage:
          !profile #TAG       → Player with specified tag
          !profile @user      → Automatically fetches if linked
          !profile            → The command author's linked account
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        tag: Optional[str] = None

        # ── 1. If Mentioned ──────────────────────────────────────────
        if ctx.message.mentions:
            mentioned = ctx.message.mentions[0]
            reverse_map = _reverse_linked_accounts()
            discord_id_str = str(mentioned.id)
            tag = reverse_map.get(discord_id_str)
            if not tag:
                await ctx.send(t("profile.no_linked_mention", mention=mentioned.mention))
                return

        # ── 2. If Tag provided ───────────────────────────────────────
        elif target:
            tag = target if target.startswith("#") else f"#{target}"

        # ── 3. If nothing provided → Author's account ───────────────
        else:
            reverse_map = _reverse_linked_accounts()
            tag = reverse_map.get(str(ctx.author.id))
            if not tag:
                await ctx.send(t("profile.no_linked_author"))
                return

        # ── Fetch from API ───────────────────────────────────────────
        async with ctx.typing():
            player = await self._get_player_data(tag)
            if not player:
                await ctx.send(t("profile.not_found", tag=tag))
                return

            # ── Extract Data ─────────────────────────────────────────
            name = player.get("name", t("profile.unknown"))
            player_tag = player.get("tag", tag)
            trophies = player.get("trophies", 0)
            best_trophies = player.get("bestTrophies", 0)
            exp_level = player.get("expLevel", 1)

            # Arena
            arena = player.get("arena", {})
            arena_name = arena.get("name", t("profile.unknown"))
            arena_emoji = _arena_emoji(arena_name)

            # Battle stats
            wins = player.get("wins", 0)
            losses = player.get("losses", 0)
            total_battles = wins + losses
            win_rate = (wins / total_battles * 100) if total_battles > 0 else 0

            three_crown_wins = player.get("threeCrownWins", 0)
            battle_count = player.get("battleCount", 0)

            # Challenge
            challenge_max_wins = player.get("challengeMaxWins", 0)
            challenge_cards_won = player.get("challengeCardsWon", 0)

            # Tournament
            tournament_cards_won = player.get("tournamentCardsWon", 0)
            tournament_battle_count = player.get("tournamentBattleCount", 0)

            # Donations
            donations = player.get("donations", 0)
            donations_received = player.get("donationsReceived", 0)
            total_donations = player.get("totalDonations", 0)

            # Favorite card
            fav_card = player.get("currentFavouriteCard", {})
            fav_card_name = fav_card.get("name", t("profile.none"))
            fav_card_icon = fav_card.get("iconUrls", {}).get("medium", "")

            # Clan info
            clan = player.get("clan", {})
            clan_name = clan.get("name", t("profile.no_clan"))
            clan_tag_str = clan.get("tag", "")
            raw_role = player.get("role", "")
            
            role_key = "war.unknown"
            if raw_role == "member": role_key = "war.role_member"
            elif raw_role == "elder": role_key = "war.role_elder"
            elif raw_role == "coLeader": role_key = "war.role_co_leader"
            elif raw_role == "leader": role_key = "war.role_leader"
                
            clan_role = t(role_key) if raw_role else ""
            clan_badge = clan.get("badgeUrls", {}).get("small", "")

            # Star Points & Total Exp
            star_points = player.get("starPoints", 0)
            total_exp = player.get("totalExpPoints", 0)

            # ── Create Embed ─────────────────────────────────────────
            embed = discord.Embed(
                title=f"👤 {name}",
                description=f"`{player_tag}`",
                color=0xF1C40F,
            )

            if fav_card_icon:
                embed.set_thumbnail(url=fav_card_icon)

            # ── Main Info ────────────────────────────────────────────
            embed.add_field(name=t("profile.trophies"), value=f"{trophies:,}", inline=True)
            embed.add_field(name=t("profile.best_trophies"), value=f"{best_trophies:,}", inline=True)
            embed.add_field(name=t("profile.level"), value=f"{exp_level}", inline=True)
            embed.add_field(name=t("profile.arena", emoji=arena_emoji), value=arena_name, inline=True)
            embed.add_field(name=t("profile.fav_card"), value=fav_card_name, inline=True)
            embed.add_field(name=t("profile.star_points"), value=f"{star_points:,}", inline=True)

            # ── Battle Stats ─────────────────────────────────────────
            wr_filled = int(win_rate / 5)
            wr_bar = "█" * wr_filled + "░" * (20 - wr_filled)

            embed.add_field(
                name=t("profile.win_rate"),
                value=t("profile.win_rate_val", total=f"{battle_count:,}", wins=f"{wins:,}", losses=f"{losses:,}", bar=wr_bar, rate=f"{win_rate:.1f}", three=f"{three_crown_wins:,}"),
                inline=False,
            )

            # ── Challenge & Tournament ───────────────────────────────
            embed.add_field(
                name=t("profile.challenge_title"),
                value=t("profile.challenge_val", max=challenge_max_wins, cards=f"{challenge_cards_won:,}"),
                inline=True,
            )
            embed.add_field(
                name=t("profile.tournament_title"),
                value=t("profile.tournament_val", battles=f"{tournament_battle_count:,}", cards=f"{tournament_cards_won:,}"),
                inline=True,
            )

            # ── Donations ────────────────────────────────────────────
            don_ratio = donations / max(donations_received, 1)
            embed.add_field(
                name=t("profile.don_title"),
                value=t("profile.don_val", don=donations, rec=donations_received, ratio=f"{don_ratio:.1f}", total=f"{total_donations:,}"),
                inline=False,
            )

            # ── Clan Info ────────────────────────────────────────────
            if clan_name != t("profile.no_clan"):
                embed.add_field(
                    name=t("profile.clan_title"),
                    value=t("profile.clan_val", name=clan_name, tag=clan_tag_str, role=clan_role),
                    inline=False,
                )

            # ── Save to database ─────────────────────────────────────
            db = self.bot.db
            await db.upsert_player(
                tag=player_tag,
                name=name,
                trophies=trophies,
                best_trophies=best_trophies,
                exp_level=exp_level,
                donations=donations,
                donations_received=donations_received,
            )

            embed.set_footer(text=t("profile.footer", exp=f"{total_exp:,}"))

        await ctx.send(embed=embed)

    @profile_cmd.error
    async def profile_error(self, ctx: commands.Context, error: Exception) -> None:
        """Profile command error handler."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(t("profile.error"))
            log.exception("Profile command error: %s", error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ProfileCog(bot))