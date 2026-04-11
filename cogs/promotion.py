"""
Promotion Cog – Suggests Elder/Co-Leader promotions based on activity scores.

Commands:
  !promotion           → Lists players with consistently high scores in recent weeks
  !promotion_history   → Shows a player's activity history

Promotion Criteria:
  - Elder suggestion    : Last 2 weeks average score >= 70
  - Co-Leader suggestion: Last 4 weeks average score >= 85
  - Members already at or above suggested rank are filtered

Source:
  Last 4 weeks of data from the database (activity_log table).
"""
import logging
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
from utils.config import clean_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)

# ── Promotion Thresholds ──────────────────────────────────────────
ELDER_THRESHOLD = 70.0       # Last 2 weeks avg >= 70
COLEADER_THRESHOLD = 85.0    # Last 4 weeks avg >= 85
MIN_WEEKS_ELDER = 2          # Minimum limit of data weeks (Elder)
MIN_WEEKS_COLEADER = 4       # Minimum limit of data weeks (Co-Leader)


def _role_priority(role: str) -> int:
    """Role priority (higher = higher rank)."""
    return {
        "member": 0,
        "elder": 1,
        "coLeader": 2,
        "leader": 3,
    }.get(role, 0)


def _role_emoji(role: str) -> str:
    """Role emoji."""
    return {
        "member": "👤",
        "elder": "🛡️",
        "coLeader": "⚜️",
        "leader": "👑",
    }.get(role, "👤")


class PromotionCog(commands.Cog, name="Promotion"):
    """Promotion suggestions based on activity score."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    # ── Helper: Fetch player scores ──────────────────────────────────

    async def _get_weekly_averages(self) -> list[dict]:
        """
        Calculates weekly average activity scores for all players.
        Fetches the last 4 weeks of data from the database.
        """
        db = self.bot.db

        # Get last 28 days of data
        today = datetime.now(timezone.utc)
        four_weeks_ago = (today - timedelta(days=28)).strftime("%Y-%m-%d")

        cursor = await db._db.execute("""
            SELECT player_tag, player_name,
                   AVG(score) as avg_score,
                   COUNT(DISTINCT recorded_at) as data_days,
                   MIN(score) as min_score,
                   MAX(score) as max_score
            FROM activity_log
            WHERE recorded_at >= ?
            GROUP BY player_tag
            ORDER BY avg_score DESC
        """, (four_weeks_ago,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def _get_recent_averages(self, player_tag: str, days: int = 14) -> float:
        """Average score of a specific player over the last N days."""
        db = self.bot.db
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor = await db._db.execute("""
            SELECT AVG(score) as avg_score
            FROM activity_log
            WHERE player_tag = ? AND recorded_at >= ?
        """, (player_tag, cutoff))
        row = await cursor.fetchone()
        return row["avg_score"] if row and row["avg_score"] else 0.0

    # ── !promotion command ──────────────────────────────────────────

    @commands.command(name="promotion", aliases=["terfi"])
    async def promotion_cmd(self, ctx: commands.Context) -> None:
        """
        Shows promotion suggestions based on activity scores.

        Criteria:
          🛡️ Elder suggestion    : Last 2 weeks avg >= 70
          ⚜️ Co-Leader suggestion: Last 4 weeks avg >= 85
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            # Get clan members and their roles
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("promotion.fetch_error"))
                return

            member_roles: dict[str, str] = {}
            member_names: dict[str, str] = {}
            for m in members:
                member_roles[m.get("tag", "")] = m.get("role", "member")
                member_names[m.get("tag", "")] = m.get("name", "Unknown")

            # Get weekly averages
            weekly_data = await self._get_weekly_averages()

            if not weekly_data:
                await ctx.send(t("promotion.insufficient_data"))
                return

            # ── Calculate promotion suggestions ───────────────────────
            elder_candidates: list[dict] = []
            coleader_candidates: list[dict] = []

            for data in weekly_data:
                tag = data["player_tag"]
                name = data["player_name"]
                avg_score = data["avg_score"]
                data_days = data["data_days"]
                min_score = data["min_score"]
                max_score = data["max_score"]

                current_role = member_roles.get(tag, "member")

                # Leaders are already at the highest rank
                if current_role == "leader":
                    continue

                # Is there enough data?
                weeks_of_data = data_days / 7.0  # approximate number of weeks

                # Last 2 weeks avg (Elder check)
                avg_2w = await self._get_recent_averages(tag, days=14)

                # Last 4 weeks avg (Co-Leader check)
                avg_4w = avg_score

                # ── Co-Leader ─────────────────────────────────────────
                if (
                    current_role in ("member", "elder")
                    and avg_4w >= COLEADER_THRESHOLD
                    and weeks_of_data >= MIN_WEEKS_COLEADER
                ):
                    coleader_candidates.append({
                        "tag": tag,
                        "name": name,
                        "current_role": current_role,
                        "avg_score": avg_4w,
                        "avg_2w": avg_2w,
                        "data_days": data_days,
                        "min_score": min_score,
                        "max_score": max_score,
                    })

                # ── Elder ─────────────────────────────────────────────
                elif (
                    current_role == "member"
                    and avg_2w >= ELDER_THRESHOLD
                    and weeks_of_data >= MIN_WEEKS_ELDER
                ):
                    elder_candidates.append({
                        "tag": tag,
                        "name": name,
                        "current_role": current_role,
                        "avg_score": avg_4w,
                        "avg_2w": avg_2w,
                        "data_days": data_days,
                        "min_score": min_score,
                        "max_score": max_score,
                    })

            # ── Create Embed ──────────────────────────────────────────
            embed = discord.Embed(
                title=t("promotion.title"),
                description=t("promotion.desc_1", elder_thresh=ELDER_THRESHOLD, coleader_thresh=COLEADER_THRESHOLD),
                color=0x2ECC71,
            )

            # ── Co-Leader Candidates ──────────────────────────────────
            if coleader_candidates:
                lines = []
                for c in coleader_candidates[:10]:
                    role_emoji = _role_emoji(c["current_role"])
                    role_name = t(f"promotion.roles.{c['current_role']}", default=c["current_role"])
                    lines.append(
                        t("promotion.coleader_line", name=c['name'], emoji=role_emoji, role=role_name, avg_4w=c['avg_score'], avg_2w=c['avg_2w'], min=c['min_score'], max=c['max_score'], days=c['data_days'])
                    )
                embed.add_field(
                    name=t("promotion.coleader_title", count=len(coleader_candidates)),
                    value="\n\n".join(lines),
                    inline=False,
                )
            else:
                embed.add_field(
                    name=t("promotion.coleader_title", count=0),
                    value=t("promotion.coleader_empty"),
                    inline=False,
                )

            # ── Elder Candidates ──────────────────────────────────────
            if elder_candidates:
                lines = []
                for c in elder_candidates[:10]:
                    lines.append(
                        t("promotion.elder_line", name=c['name'], avg_4w=c['avg_score'], avg_2w=c['avg_2w'], min=c['min_score'], max=c['max_score'], days=c['data_days'])
                    )
                embed.add_field(
                    name=t("promotion.elder_title", count=len(elder_candidates)),
                    value="\n\n".join(lines),
                    inline=False,
                )
            else:
                embed.add_field(
                    name=t("promotion.elder_title", count=0),
                    value=t("promotion.elder_empty"),
                    inline=False,
                )

            # Footer
            total = len(coleader_candidates) + len(elder_candidates)
            embed.set_footer(
                text=t("promotion.footer", total=total)
            )

        await ctx.send(embed=embed)

    # ── !promotion_history command ────────────────────────────────────

    @commands.command(name="promotion_history", aliases=["terfi_gecmis", "terfi_geçmiş"])
    async def promotion_history_cmd(self, ctx: commands.Context, player_tag: str = None) -> None:
        """
        Shows a player's activity score history.

        Usage:
          !promotion_history #TAG  → Specified player's history
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if not player_tag:
            await ctx.send(t("promotion.history_usage"))
            return

        if not player_tag.startswith("#"):
            player_tag = f"#{player_tag}"

        async with ctx.typing():
            db = self.bot.db
            history = await db.get_player_activity_history(player_tag, limit=30)

            if not history:
                await ctx.send(t("promotion.history_no_data", tag=player_tag))
                return

            name = history[0].get("player_name", "Unknown")

            embed = discord.Embed(
                title=t("promotion.history_title", name=name),
                color=0x3498DB,
            )

            lines = []
            for entry in history[:20]:
                date = entry.get("recorded_at", "?")
                score = entry.get("score", 0)
                don_s = entry.get("donation_score", 0)
                war_s = entry.get("war_score", 0)
                tro_s = entry.get("trophy_score", 0)

                # Mini bar
                bar_len = int(score / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)

                lines.append(
                    t("promotion.history_line", date=date, bar=bar, score=score, don=don_s, war=war_s, tro=tro_s)
                )

            embed.description = "\n".join(lines)

            # Calc averages
            avg = sum(e.get("score", 0) for e in history) / max(len(history), 1)
            max_score = max(e.get("score", 0) for e in history)
            min_score = min(e.get("score", 0) for e in history)

            embed.set_footer(
                text=t("promotion.history_footer", avg=avg, max=max_score, min=min_score, count=len(history))
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PromotionCog(bot))