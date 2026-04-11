"""
Activity Cog – Combines donation, war, and trophy data under a single score.

Commands:
  !activity          → Shows activity score (0-100) for all members
  !kicklist [number] → Suggests N members with lowest scores (default 5, customizable)

Score Formula:
  score = (donation_ratio * 30) + (war_participation * 50) + (trophy_change * 20)
    - donation_ratio    : Player's donation / clan's max donation (0-1)
    - war_participation : Player's fame / clan's max fame (0-1)
    - trophy_change     : Normalized trophy change (0-1, negative becomes 0)

Automatic:
  Calculates and saves scores to the database every 6 hours.
"""
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import clean_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)


def _calculate_activity_scores(
    members: list[dict],
    participants: list[dict] | None,
    trophy_changes: dict[str, int],
) -> list[dict]:
    """
    Calculates activity scores for all members.
    """
    max_donation = max((m.get("donations", 0) for m in members), default=1)
    max_donation = max(max_donation, 1)

    participant_map: dict[str, dict] = {}
    max_fame = 1
    if participants:
        for p in participants:
            participant_map[p.get("tag", "")] = p
        max_fame = max((p.get("fame", 0) for p in participants), default=1)
        max_fame = max(max_fame, 1)

    trophy_values = list(trophy_changes.values()) if trophy_changes else [0]
    max_trophy_change = max(max(trophy_values), 1) if trophy_values else 1

    results: list[dict] = []
    for m in members:
        tag = m.get("tag", "")
        name = m.get("name", "Unknown")
        donations = m.get("donations", 0)

        donation_ratio = min(donations / max_donation, 1.0)
        donation_score = donation_ratio * 30

        p_data = participant_map.get(tag)
        if p_data:
            fame = p_data.get("fame", 0)
            war_ratio = min(fame / max_fame, 1.0)
        else:
            war_ratio = 0.0
        war_score = war_ratio * 50

        trophy_change = trophy_changes.get(tag, 0)
        if trophy_change > 0:
            trophy_ratio = min(trophy_change / max_trophy_change, 1.0)
        else:
            trophy_ratio = 0.0
        trophy_score = trophy_ratio * 20

        total_score = round(donation_score + war_score + trophy_score, 1)
        total_score = min(total_score, 100.0)

        results.append({
            "tag": tag,
            "name": name,
            "score": total_score,
            "donation_score": round(donation_score, 1),
            "war_score": round(war_score, 1),
            "trophy_score": round(trophy_score, 1),
            "donations": donations,
            "fame": p_data.get("fame", 0) if p_data else 0,
            "trophy_change": trophy_change,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _score_emoji(score: float) -> str:
    if score >= 80:
        return "🟢"
    elif score >= 60:
        return "🟡"
    elif score >= 40:
        return "🟠"
    elif score >= 20:
        return "🔴"
    else:
        return "⚫"


def _score_bar(score: float) -> str:
    filled = int(score / 5)
    return "█" * filled + "░" * (20 - filled)


class ActivityCog(commands.Cog, name="Activity"):
    """Activity score and kick list commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    def cog_unload(self) -> None:
        self.auto_score_update.cancel()

    async def _fetch_and_calculate(self) -> list[dict] | None:
        members = await self.api.get_clan_members()
        if not members:
            return None

        race = await self.api.get_current_river_race()
        participants = None
        if race and "clan" in race:
            participants = race["clan"].get("participants", [])

        trophy_changes: dict[str, int] = {}
        db = self.bot.db
        for m in members:
            tag = m.get("tag", "")
            change = await db.get_trophy_change(tag, days=7)
            trophy_changes[tag] = change
            await db.save_trophy_snapshot(tag, m.get("trophies", 0))

        await db.upsert_many_players(members)

        return _calculate_activity_scores(members, participants, trophy_changes)

    # ── !activity ─────────────────────────────────────────────────────

    @commands.command(name="activity", aliases=["aktivite"])
    async def activity_cmd(self, ctx: commands.Context) -> None:
        """Shows activity scores of all members (!activity)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            scores = await self._fetch_and_calculate()
            if scores is None:
                await ctx.send(t("activity.fetch_error"))
                return

            embeds: list[discord.Embed] = []
            page_size = 25
            total_pages = (len(scores) + page_size - 1) // page_size

            for page in range(total_pages):
                start = page * page_size
                end = min(start + page_size, len(scores))
                page_scores = scores[start:end]

                title_suffix = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""
                embed = discord.Embed(
                    title=t("activity.table_title") + title_suffix,
                    description=t("activity.table_desc"),
                    color=0x2ECC71,
                )

                lines = []
                for i, s in enumerate(page_scores, start + 1):
                    emoji = _score_emoji(s["score"])
                    bar = _score_bar(s["score"])
                    name = s["name"][:15]
                    lines.append(
                        f"**{i}.** {emoji} **{name}** `{bar}` **{s['score']}**/100\n"
                        f"    📤{s['donations']} | ⚔️{s['fame']} | 🏆{s['trophy_change']:+}"
                    )

                embed.description += "\n".join(lines)

                if page == 0:
                    avg_score = sum(s["score"] for s in scores) / max(len(scores), 1)
                    embed.set_footer(
                        text=t("activity.avg_footer", avg=f"{avg_score:.1f}", count=len(scores))
                    )

                embeds.append(embed)

            for embed in embeds:
                await ctx.send(embed=embed)

    # ── !kicklist ─────────────────────────────────────────────────────

    @commands.command(name="kicklist")
    async def kicklist(self, ctx: commands.Context, count: int = 5) -> None:
        """Suggests members with the lowest activity score."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if count < 1:
            await ctx.send(t("activity.min_args_err"))
            return
        if count > 50:
            await ctx.send(t("activity.max_args_err"))
            return

        async with ctx.typing():
            scores = await self._fetch_and_calculate()
            if scores is None:
                await ctx.send(t("activity.fetch_error"))
                return

            members = await self.api.get_clan_members()
            leader_tags = set()
            if members:
                for m in members:
                    role = m.get("role", "member")
                    if role in ("leader", "coLeader"):
                        leader_tags.add(m.get("tag", ""))

            kickable = [s for s in scores if s["tag"] not in leader_tags]
            kickable.sort(key=lambda x: x["score"])

            kick_list = kickable[:count]

            if not kick_list:
                await ctx.send(t("activity.kick_no_rec"))
                return

            embed = discord.Embed(
                title=t("activity.kick_title", count=len(kick_list)),
                description=t("activity.kick_desc"),
                color=0xE74C3C,
            )

            lines = []
            for i, s in enumerate(kick_list, 1):
                emoji = _score_emoji(s["score"])
                bar = _score_bar(s["score"])
                name = s["name"]
                
                line_str = t("activity.kick_line", don=s['donations'], fame=s['fame'], trophy=s['trophy_change'])
                lines.append(
                    f"**{i}.** {emoji} **{name}** `{bar}` **{s['score']}**/100\n{line_str}"
                )

            embed.description += "\n".join(lines)

            avg_kick = sum(s["score"] for s in kick_list) / max(len(kick_list), 1)
            avg_clan = sum(s["score"] for s in scores) / max(len(scores), 1)
            embed.set_footer(
                text=t("activity.kick_footer", avg_kick=f"{avg_kick:.1f}", avg_clan=f"{avg_clan:.1f}", shown=len(kick_list), total=len(kickable))
            )

        await ctx.send(embed=embed)

    @tasks.loop(hours=6)
    async def auto_score_update(self) -> None:
        """Saves scores of all members to the database every 6 hours."""
        scores = await self._fetch_and_calculate()
        if not scores:
            return

        db = self.bot.db
        for s in scores:
            await db.save_activity_score(
                player_tag=s["tag"],
                player_name=s["name"],
                score=s["score"],
                donation_score=s["donation_score"],
                war_score=s["war_score"],
                trophy_score=s["trophy_score"],
            )
        log.info("Automatic activity score updated: %d members", len(scores))

    @auto_score_update.before_loop
    async def before_auto_score(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = ActivityCog(bot)
    await bot.add_cog(cog)
    cog.auto_score_update.start()