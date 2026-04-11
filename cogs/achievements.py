"""
Achievements Cog – Badges players can earn.
Notifications are sent to the "badges" channel.
"""
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import CHANNEL_ID
from utils.channels import get_notification_channel
import utils.i18n as i18n

log = logging.getLogger(__name__)


class AchievementsCog(commands.Cog, name="Achievements"):
    """Achievement badge system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    def cog_unload(self) -> None:
        self.badge_check_task.cancel()

    async def _ensure_table(self) -> None:
        db = self.bot.db
        await db._db.executescript("""
            CREATE TABLE IF NOT EXISTS achievements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_tag  TEXT NOT NULL,
                player_name TEXT NOT NULL,
                badge_id    TEXT NOT NULL,
                earned_at   TEXT NOT NULL,
                UNIQUE(player_tag, badge_id)
            );
        """)
        await db._db.commit()

    async def _has_badge(self, player_tag: str, badge_id: str) -> bool:
        db = self.bot.db
        cursor = await db._db.execute(
            "SELECT 1 FROM achievements WHERE player_tag = ? AND badge_id = ?",
            (player_tag, badge_id),
        )
        return await cursor.fetchone() is not None

    async def _grant_badge(self, player_tag: str, player_name: str, badge_id: str) -> bool:
        if await self._has_badge(player_tag, badge_id):
            return False

        db = self.bot.db
        now = datetime.now(timezone.utc).isoformat()
        await db._db.execute(
            "INSERT INTO achievements (player_tag, player_name, badge_id, earned_at) VALUES (?, ?, ?, ?)",
            (player_tag, player_name, badge_id, now),
        )
        await db._db.commit()
        log.info("Badge granted: %s → %s (%s)", player_name, badge_id, player_tag)
        return True

    async def _get_player_badges(self, player_tag: str) -> list[dict]:
        db = self.bot.db
        cursor = await db._db.execute(
            "SELECT * FROM achievements WHERE player_tag = ? ORDER BY earned_at",
            (player_tag,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def _get_badge_leaderboard(self) -> list[dict]:
        db = self.bot.db
        cursor = await db._db.execute("""
            SELECT player_tag, player_name, COUNT(*) as badge_count
            FROM achievements
            GROUP BY player_tag
            ORDER BY badge_count DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def _check_all_badges(self) -> list[tuple[str, str, str]]:
        await self._ensure_table()

        members = await self.api.get_clan_members()
        if not members:
            return []

        race = await self.api.get_current_river_race()
        participant_map: dict[str, dict] = {}
        if race and "clan" in race:
            for p in race["clan"].get("participants", []):
                participant_map[p.get("tag", "")] = p

        db = self.bot.db
        newly_earned: list[tuple[str, str, str]] = []

        for m in members:
            tag = m.get("tag", "")
            name = m.get("name", "Unknown")
            donations = m.get("donations", 0)
            p_data = participant_map.get(tag)
            fame = p_data.get("fame", 0) if p_data else 0

            # 🎖️ First Blood
            if fame > 0:
                if await self._grant_badge(tag, name, "first_blood"):
                    newly_earned.append((name, "first_blood", "🎖️"))

            # 💎 Donation King
            if donations >= 200:
                if await self._grant_badge(tag, name, "donation_king"):
                    newly_earned.append((name, "donation_king", "💎"))

            # 🏆 War Machine
            war_hist = await db.get_war_history(tag, limit=50)
            total_fame = sum(w.get("fame", 0) for w in war_hist)
            if total_fame >= 10000:
                if await self._grant_badge(tag, name, "war_machine"):
                    newly_earned.append((name, "war_machine", "🏆"))

            # 📤 Generous Spirit
            don_hist = await db.get_donation_history(tag, limit=50)
            total_donations = sum(d.get("donations", 0) for d in don_hist)
            if total_donations >= 1000:
                if await self._grant_badge(tag, name, "generous_spirit"):
                    newly_earned.append((name, "generous_spirit", "📤"))

            # 🔥 Fire Streak
            if len(war_hist) >= 4:
                last_4 = war_hist[:4]
                all_active = all(w.get("fame", 0) > 0 for w in last_4)
                if all_active:
                    if await self._grant_badge(tag, name, "fire_streak"):
                        newly_earned.append((name, "fire_streak", "🔥"))

            # 🛡️ Loyal Soldier
            activity_hist = await db.get_player_activity_history(tag, limit=100)
            if len(activity_hist) >= 90:
                if await self._grant_badge(tag, name, "loyal_soldier"):
                    newly_earned.append((name, "loyal_soldier", "🛡️"))

            # 🎯 Perfectionist
            for entry in activity_hist:
                if entry.get("score", 0) >= 90:
                    if await self._grant_badge(tag, name, "perfectionist"):
                        newly_earned.append((name, "perfectionist", "🎯"))
                    break

        # ⚡ MVP
        if participant_map:
            max_fame_player = max(
                participant_map.values(), key=lambda p: p.get("fame", 0)
            )
            if max_fame_player.get("fame", 0) > 0:
                mvp_tag = max_fame_player.get("tag", "")
                mvp_name = max_fame_player.get("name", "Unknown")
                if await self._grant_badge(mvp_tag, mvp_name, "mvp"):
                    newly_earned.append((mvp_name, "mvp", "⚡"))

        # 👑 Legend
        for m in members:
            tag = m.get("tag", "")
            name = m.get("name", "Unknown")
            badges = await self._get_player_badges(tag)
            non_legend = [b for b in badges if b["badge_id"] != "legend"]
            if len(non_legend) >= 5:
                if await self._grant_badge(tag, name, "legend"):
                    newly_earned.append((name, "legend", "👑"))

        return newly_earned

    # ── Commands ─────────────────────────────────────────────────────

    @commands.command(name="badges", aliases=["rozetlerim"])
    async def badges_cmd(self, ctx: commands.Context, player_tag: str = None) -> None:
        """Shows earned badges (!badges or !badges #TAG)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        await self._ensure_table()

        if not player_tag:
            import json, os
            linked_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "linked_accounts.json"
            )
            try:
                with open(linked_path, encoding="utf-8") as f:
                    linked = json.load(f)
                reverse = {v: k for k, v in linked.items()}
                player_tag = reverse.get(str(ctx.author.id))
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            if not player_tag:
                await ctx.send(t("achievements.no_account"))
                return

        if not player_tag.startswith("#"):
            player_tag = f"#{player_tag}"

        async with ctx.typing():
            badges = await self._get_player_badges(player_tag)

            if not badges:
                await ctx.send(t("achievements.no_badges_yet", tag=player_tag))
                return

            name = badges[0].get("player_name", "Unknown")

            embed = discord.Embed(
                title=t("achievements.badges_title", name=name),
                description=t("achievements.badges_desc", count=len(badges)),
                color=0xF1C40F,
            )

            for badge_data in badges:
                bid = badge_data["badge_id"]
                emoji = t(f"achievements.badges.{bid}.emoji", default="❓")
                # Using hardcoded emojis if not defined in i18n:
                emoji_map = {
                    "first_blood": "🎖️",
                    "fire_streak": "🔥",
                    "donation_king": "💎",
                    "loyal_soldier": "🛡️",
                    "mvp": "⚡",
                    "war_machine": "🏆",
                    "generous_spirit": "📤",
                    "perfectionist": "🎯",
                    "legend": "👑",
                }
                emoji = emoji_map.get(bid, "❓")
                bname = t(f"achievements.badges.{bid}.name")
                desc = t(f"achievements.badges.{bid}.desc")
                earned = badge_data.get("earned_at", "?")[:10]

                embed.description += f"{emoji} **{bname}** – {desc}\n{t('achievements.earned_at', date=earned)}"

            earned_ids = {b["badge_id"] for b in badges}
            missing = [bid for bid in emoji_map if bid not in earned_ids]
            if missing:
                missing_text = " ".join(
                    f"~~{emoji_map[bid]}~~" for bid in missing
                )
                embed.add_field(
                    name=t("achievements.unearned_badges"),
                    value=missing_text,
                    inline=False,
                )

        await ctx.send(embed=embed)

    @commands.command(name="badge_leaderboard", aliases=["rozet_siralamasi", "rozet_sıralaması"])
    async def leaderboard_cmd(self, ctx: commands.Context) -> None:
        """Leaderboard of members with most badges (!badge_leaderboard)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        await self._ensure_table()

        async with ctx.typing():
            leaderboard = await self._get_badge_leaderboard()

            if not leaderboard:
                await ctx.send(t("achievements.leaderboard.no_badges"))
                return

            embed = discord.Embed(
                title=t("achievements.leaderboard.title"),
                color=0xE67E22,
            )

            lines = []
            
            emoji_map = {
                "first_blood": "🎖️",
                "fire_streak": "🔥",
                "donation_king": "💎",
                "loyal_soldier": "🛡️",
                "mvp": "⚡",
                "war_machine": "🏆",
                "generous_spirit": "📤",
                "perfectionist": "🎯",
                "legend": "👑",
            }
            
            for i, entry in enumerate(leaderboard[:20], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                name = entry["player_name"]
                count = entry["badge_count"]

                badges = await self._get_player_badges(entry["player_tag"])
                badge_emojis = " ".join(
                    emoji_map.get(b["badge_id"], "❓")
                    for b in badges
                )

                lines.append(
                    t("achievements.leaderboard.line", medal=medal, name=name, count=count, emojis=badge_emojis)
                )

            embed.description = "\n\n".join(lines)
            embed.set_footer(text=t("achievements.leaderboard.footer", count=len(leaderboard)))

        await ctx.send(embed=embed)

    @commands.command(name="all_badges", aliases=["rozetler"])
    async def all_badges_cmd(self, ctx: commands.Context) -> None:
        """Shows all badge descriptions (!all_badges)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        embed = discord.Embed(
            title=t("achievements.all_badges.title"),
            description=t("achievements.all_badges.desc"),
            color=0x9B59B6,
        )

        emoji_map = {
            "first_blood": "🎖️",
            "fire_streak": "🔥",
            "donation_king": "💎",
            "loyal_soldier": "🛡️",
            "mvp": "⚡",
            "war_machine": "🏆",
            "generous_spirit": "📤",
            "perfectionist": "🎯",
            "legend": "👑",
        }

        for bid, emoji in emoji_map.items():
            name = t(f"achievements.badges.{bid}.name")
            desc = t(f"achievements.badges.{bid}.desc")
            embed.description += (
                f"{emoji} **{name}**\n"
                f"   {desc}\n\n"
            )

        embed.set_footer(text=t("achievements.all_badges.footer"))
        await ctx.send(embed=embed)

    # ── Auto Badge Check → badges channel ───────────────────────────

    @tasks.loop(hours=6)
    async def badge_check_task(self) -> None:
        newly_earned = await self._check_all_badges()

        if not newly_earned:
            return

        channel = await get_notification_channel(self.bot, "badges", CHANNEL_ID)
        if channel is None:
            return
            
        guild_id = channel.guild.id if hasattr(channel, "guild") else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)

        lines = []
        for name, badge_id, emoji in newly_earned:
            badge_name = t(f"achievements.badges.{badge_id}.name")
            lines.append(t("achievements.notification.line", emoji=emoji, name=name, badge_name=badge_name))

        if lines:
            embed = discord.Embed(
                title=t("achievements.notification.title"),
                description="\n".join(lines),
                color=0xF1C40F,
            )
            embed.set_footer(text=t("achievements.notification.footer"))
            await channel.send(embed=embed)

        log.info("Badge check completed: %d new badges", len(newly_earned))

    @badge_check_task.before_loop
    async def before_badge_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = AchievementsCog(bot)
    await bot.add_cog(cog)
    cog.badge_check_task.start()