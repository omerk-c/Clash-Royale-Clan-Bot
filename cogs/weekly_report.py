"""
Weekly Report Cog – Automatic performance summary every Monday morning.
Notifications are sent to the "reports" channel.
"""
import json
import logging
import os
from datetime import datetime, time, timezone, timedelta

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import CHANNEL_ID
from utils.channels import get_notification_channel
import utils.i18n as i18n

log = logging.getLogger(__name__)

SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "weekly_settings.json"
)


def _load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"enabled": True}


def _save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def _week_start_str() -> str:
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


class WeeklyReportCog(commands.Cog, name="Weekly Report"):
    """Automatic weekly performance report."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    def cog_unload(self) -> None:
        self.weekly_report_task.cancel()
        self.weekly_snapshot_task.cancel()

    async def _generate_report(self, guild_id: int = 0) -> discord.Embed | None:
        def t(key, **kw): return i18n.get(guild_id, key, **kw)
        
        clan = await self.api.get_clan_info()
        if not clan:
            return None

        members = await self.api.get_clan_members()
        if not members:
            return None

        race = await self.api.get_current_river_race()
        participant_map: dict[str, dict] = {}
        if race and "clan" in race:
            for p in race["clan"].get("participants", []):
                participant_map[p.get("tag", "")] = p

        db = self.bot.db
        activity_scores = await db.get_activity_scores()

        sorted_by_donation = sorted(members, key=lambda m: m.get("donations", 0), reverse=True)

        fame_list = []
        for m in members:
            tag = m.get("tag", "")
            p_data = participant_map.get(tag)
            fame = p_data.get("fame", 0) if p_data else 0
            fame_list.append({"name": m["name"], "tag": tag, "fame": fame})
        sorted_by_fame = sorted(fame_list, key=lambda x: x["fame"], reverse=True)

        most_active = None
        least_active = None
        if activity_scores:
            sorted_by_activity = sorted(activity_scores, key=lambda x: x.get("score", 0), reverse=True)
            most_active = sorted_by_activity[0] if sorted_by_activity else None
            least_active = sorted_by_activity[-1] if sorted_by_activity else None

        clan_score = clan.get("clanScore", 0)

        today = datetime.now(timezone.utc)
        week_ago = today - timedelta(days=7)
        date_range = f"{week_ago.strftime('%d.%m.%Y')} – {today.strftime('%d.%m.%Y')}"

        embed = discord.Embed(
            title=t("weekly_report.title"),
            description=t("weekly_report.desc_date_clan", date=date_range, clan=clan['name']),
            color=0xF39C12,
        )
        embed.set_thumbnail(url=clan.get("badgeUrls", {}).get("medium", ""))

        if most_active:
            embed.add_field(
                name=t("weekly_report.most_active"),
                value=t("weekly_report.most_active_val", name=most_active.get('player_name', '?'), score=most_active.get('score', 0)),
                inline=True,
            )

        if sorted_by_donation:
            top_donor = sorted_by_donation[0]
            embed.add_field(
                name=t("weekly_report.top_donor"),
                value=t("weekly_report.top_donor_val", name=top_donor['name'], amount=top_donor.get('donations', 0)),
                inline=True,
            )

        if sorted_by_fame and sorted_by_fame[0]["fame"] > 0:
            top_fame = sorted_by_fame[0]
            embed.add_field(
                name=t("weekly_report.top_fame"),
                value=t("weekly_report.top_fame_val", name=top_fame['name'], amount=top_fame['fame']),
                inline=True,
            )

        if least_active:
            embed.add_field(
                name=t("weekly_report.least_active"),
                value=t("weekly_report.least_active_val", name=least_active.get('player_name', '?'), score=least_active.get('score', 0)),
                inline=True,
            )

        total_donations = sum(m.get("donations", 0) for m in members)
        total_donations_received = sum(m.get("donationsReceived", 0) for m in members)
        avg_donation = total_donations / max(len(members), 1)
        total_fame_all = sum(f["fame"] for f in fame_list)

        embed.add_field(
            name=t("weekly_report.clan_overview"),
            value=t("weekly_report.clan_overview_val", members=len(members), trophies=clan_score, war_wins=clan.get('warWins', 0)),
            inline=True,
        )

        embed.add_field(
            name=t("weekly_report.donation_summary"),
            value=t("weekly_report.donation_summary_val", total_don=total_donations, total_rec=total_donations_received, avg=avg_donation),
            inline=False,
        )

        if total_fame_all > 0:
            embed.add_field(
                name=t("weekly_report.war_summary"),
                value=t("weekly_report.war_summary_val", total_fame=total_fame_all, participants=len([f for f in fame_list if f['fame'] > 0]), members=len(members)),
                inline=False,
            )

        top5_don = "\n".join(
            t("weekly_report.top5_donors_line", index=i, name=m['name'], amount=m.get('donations', 0))
            for i, m in enumerate(sorted_by_donation[:5], 1)
        )
        if top5_don:
            embed.add_field(name=t("weekly_report.top5_donors"), value=top5_don, inline=True)

        top5_fame = "\n".join(
            t("weekly_report.top5_warriors_line", index=i, name=f['name'], amount=f['fame'])
            for i, f in enumerate(sorted_by_fame[:5], 1)
            if f["fame"] > 0
        )
        if top5_fame:
            embed.add_field(name=t("weekly_report.top5_warriors"), value=top5_fame, inline=True)

        embed.set_footer(text=t("weekly_report.footer"))
        return embed

    @commands.command(name="weekly", aliases=["haftalik", "haftalık"])
    async def weekly_cmd(self, ctx: commands.Context) -> None:
        """Shows instant weekly performance report (!weekly)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            embed = await self._generate_report(ctx.guild.id if ctx.guild else 0)
            if embed is None:
                await ctx.send(t("weekly_report.report_failed"))
                return
        await ctx.send(embed=embed)

    @commands.command(name="weekly_setting", aliases=["haftalik_ayar", "haftalık_ayar"])
    async def weekly_setting_cmd(self, ctx: commands.Context) -> None:
        """Toggles the automatic weekly report on/off (!weekly_setting)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        settings = _load_settings()
        current = settings.get("enabled", True)
        settings["enabled"] = not current
        _save_settings(settings)
        
        status = t("weekly_report.status_on") if settings["enabled"] else t("weekly_report.status_off")
        await ctx.send(t("weekly_report.status_msg", status=status))

    @tasks.loop(time=time(hour=21, minute=0, tzinfo=timezone.utc))
    async def weekly_snapshot_task(self) -> None:
        today = datetime.now(timezone.utc)
        if today.weekday() != 6:
            return

        members = await self.api.get_clan_members()
        if not members:
            return

        race = await self.api.get_current_river_race()
        participant_map: dict[str, dict] = {}
        if race and "clan" in race:
            for p in race["clan"].get("participants", []):
                participant_map[p.get("tag", "")] = p

        db = self.bot.db
        week = _week_start_str()

        for m in members:
            tag = m.get("tag", "")
            name = m.get("name", "Unknown")

            await db.save_donation_snapshot(
                player_tag=tag, player_name=name,
                donations=m.get("donations", 0),
                donations_received=m.get("donationsReceived", 0),
                week_start=week,
            )

            p_data = participant_map.get(tag)
            if p_data:
                await db.save_war_snapshot(
                    player_tag=tag, player_name=name,
                    fame=p_data.get("fame", 0),
                    decks_used=p_data.get("decksUsed", 0),
                    boat_attacks=p_data.get("boatAttacks", 0),
                    week_start=week,
                )

        log.info("Weekly snapshot saved: %d members, week %s", len(members), week)

    @weekly_snapshot_task.before_loop
    async def before_snapshot(self) -> None:
        await self.bot.wait_until_ready()

    # ── Auto Weekly Report → reports channel ──────────────────────────

    @tasks.loop(time=time(hour=8, minute=0, tzinfo=timezone.utc))
    async def weekly_report_task(self) -> None:
        today = datetime.now(timezone.utc)
        if today.weekday() != 0:
            return

        settings = _load_settings()
        if not settings.get("enabled", True):
            return

        channel = await get_notification_channel(self.bot, "reports", CHANNEL_ID)
        if channel is None:
            return
            
        guild_id = channel.guild.id if hasattr(channel, "guild") else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)

        embed = await self._generate_report(guild_id)
        if embed is None:
            return

        await channel.send(t("weekly_report.notification_title"), embed=embed)
        log.info("Weekly automatic report sent.")

    @weekly_report_task.before_loop
    async def before_weekly_report(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = WeeklyReportCog(bot)
    await bot.add_cog(cog)
    cog.weekly_report_task.start()
    cog.weekly_snapshot_task.start()