"""
Tracker Cog – Tracks donation/war activity (batched), member joins/leaves, and periodic reports.
All tracking is tag-based (safe against name changes).
Notifications are routed to correct channels via the channel manager.
"""
import logging
from collections import defaultdict

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import CHANNEL_ID
from utils.channels import get_notification_channel
import utils.i18n as i18n

log = logging.getLogger(__name__)


class TrackerCog(commands.Cog, name="Tracker"):
    """Automatic activity tracking and periodic reporting."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

        # ── Tag-based state ──────────────────────────────────────────
        self._donations: dict[str, int] = {}
        self._war_points: dict[str, int] = {}
        self._known_members: dict[str, str] = {}  # tag → name

        # Batched changes
        self._pending_changes: dict[str, dict] = defaultdict(
            lambda: {"name": "", "donation_diff": 0, "war_diff": 0}
        )

        self._initialized = False

    def cog_unload(self) -> None:
        self.check_changes.cancel()
        self.send_batched_report.cancel()
        self.clan_member_check.cancel()
        self.auto_report.cancel()

    # ── Initial load ─────────────────────────────────────────────────

    async def _initialize_state(self) -> None:
        members = await self.api.get_clan_members()
        for m in members:
            tag = m["tag"]
            self._donations[tag] = m.get("donations", 0)
            self._war_points[tag] = m.get("warDayPoints", 0) if "warDayPoints" in m else 0
            self._known_members[tag] = m["name"]
        self._initialized = True
        log.info("Tracker started – recorded %d members.", len(members))

    # ── Change Tracking (every 10 min) ───────────────────────────────────

    @tasks.loop(minutes=10)
    async def check_changes(self) -> None:
        if not self._initialized:
            await self._initialize_state()
            return

        members = await self.api.get_clan_members()
        if not members:
            return

        for m in members:
            tag = m["tag"]
            name = m["name"]
            don = m.get("donations", 0)
            war = m.get("warDayPoints", 0) if "warDayPoints" in m else 0

            if tag in self._donations:
                diff = don - self._donations[tag]
                if diff > 0:
                    self._pending_changes[tag]["name"] = name
                    self._pending_changes[tag]["donation_diff"] += diff

            if tag in self._war_points:
                diff_w = war - self._war_points[tag]
                if diff_w > 0:
                    self._pending_changes[tag]["name"] = name
                    self._pending_changes[tag]["war_diff"] += diff_w

            self._donations[tag] = don
            self._war_points[tag] = war
            self._known_members[tag] = name

    @check_changes.before_loop
    async def before_check_changes(self) -> None:
        await self.bot.wait_until_ready()

    # ── Batched Report (every 60 min) → activity channel ──────────────────

    @tasks.loop(minutes=60)
    async def send_batched_report(self) -> None:
        channel = await get_notification_channel(self.bot, "activity", CHANNEL_ID)
        guild_id = channel.guild.id if channel and getattr(channel, "guild", None) else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)
        
        if channel is None or not self._pending_changes:
            return

        embed = discord.Embed(
            title=t("tracker.active_title"),
            color=0x3498DB,
        )

        don_lines = []
        for tag, data in sorted(
            self._pending_changes.items(),
            key=lambda x: x[1]["donation_diff"],
            reverse=True,
        ):
            if data["donation_diff"] > 0:
                don_lines.append(t("tracker.donations_line", name=data["name"], diff=data["donation_diff"]))

        war_lines = []
        for tag, data in sorted(
            self._pending_changes.items(),
            key=lambda x: x[1]["war_diff"],
            reverse=True,
        ):
            if data["war_diff"] > 0:
                war_lines.append(t("tracker.war_line", name=data["name"], diff=data["war_diff"]))

        if don_lines:
            embed.add_field(
                name=t("tracker.donations_field"),
                value="\n".join(don_lines[:15]) or t("tracker.none"),
                inline=False,
            )
        if war_lines:
            embed.add_field(
                name=t("tracker.war_field"),
                value="\n".join(war_lines[:15]) or t("tracker.none"),
                inline=False,
            )

        if don_lines or war_lines:
            await channel.send(embed=embed)

        self._pending_changes.clear()

    @send_batched_report.before_loop
    async def before_batched_report(self) -> None:
        await self.bot.wait_until_ready()

    # ── Member Join/Leave Tracking (every 2 min) → members channel ─────────

    @tasks.loop(minutes=2)
    async def clan_member_check(self) -> None:
        if not self._initialized:
            return

        channel = await get_notification_channel(self.bot, "members", CHANNEL_ID)
        guild_id = channel.guild.id if channel and getattr(channel, "guild", None) else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)
        
        if channel is None:
            return

        members = await self.api.get_clan_members()
        if not members:
            return

        current_tags = {m["tag"]: m["name"] for m in members}
        old_tags = set(self._known_members.keys())
        new_tags = set(current_tags.keys())

        joined = new_tags - old_tags
        left = old_tags - new_tags

        for tag in joined:
            name = current_tags[tag]
            await channel.send(t("tracker.joined", name=name, tag=tag))

        for tag in left:
            name = self._known_members.get(tag, t("tracker.unknown"))
            try:
                player_info = await self.api.get_player_info(tag)
                if player_info:
                    player_clan = player_info.get("clan")
                    if player_clan:
                        new_clan_name = player_clan.get("name", t("tracker.unknown"))
                        await channel.send(t("tracker.left_voluntary", name=name, tag=tag, new_clan=new_clan_name))
                    else:
                        await channel.send(t("tracker.kicked", name=name, tag=tag))
                else:
                    await channel.send(t("tracker.left_unknown", name=name, tag=tag))
            except Exception:
                await channel.send(t("tracker.left_general", name=name, tag=tag))

        self._known_members = current_tags

    @clan_member_check.before_loop
    async def before_member_check(self) -> None:
        await self.bot.wait_until_ready()

    # ── Auto Clan Report (every 2 hours) → reports channel ───────────

    @tasks.loop(minutes=120)
    async def auto_report(self) -> None:
        channel = await get_notification_channel(self.bot, "reports", CHANNEL_ID)
        guild_id = channel.guild.id if channel and getattr(channel, "guild", None) else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)
        
        if channel is None:
            return

        clan = await self.api.get_clan_info()
        if not clan:
            return

        members = await self.api.get_clan_members()
        if not members:
            return

        embed = discord.Embed(
            title=t("tracker.report_title", clan_name=clan['name']),
            color=0xF39C12,
        )
        embed.set_thumbnail(url=clan.get("badgeUrls", {}).get("medium", ""))
        embed.add_field(name=t("tracker.trophies"), value=f"{clan.get('clanScore', '?'):,}")
        embed.add_field(name=t("tracker.members"), value=f"{clan.get('members', '?')}/50")
        embed.add_field(name=t("tracker.level"), value=clan.get("clanLevel", "?"))
        embed.add_field(name=t("tracker.war_wins"), value=str(clan.get("warWins", 0)))

        desc = clan.get("description", t("tracker.none"))[:1024]
        embed.add_field(name=t("tracker.description"), value=desc, inline=False)

        sorted_don = sorted(members, key=lambda m: m.get("donations", 0), reverse=True)
        don_text = "\n".join(
            t("tracker.donor_line", name=m['name'], donations=m.get('donations', 0)) for m in sorted_don[:5]
        ) or t("tracker.none")
        embed.add_field(name=t("tracker.top_donors"), value=don_text, inline=False)

        await channel.send(embed=embed)

    @auto_report.before_loop
    async def before_auto_report(self) -> None:
        await self.bot.wait_until_ready()

    # ── Discord Server Join/Leave → members channel ─────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = await get_notification_channel(self.bot, "members", CHANNEL_ID)
        if channel:
            guild_id = channel.guild.id if hasattr(channel, "guild") else 0
            await channel.send(i18n.get(guild_id, "tracker.welcome_discord", name=member.display_name))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel = await get_notification_channel(self.bot, "members", CHANNEL_ID)
        if channel:
            guild_id = channel.guild.id if hasattr(channel, "guild") else 0
            await channel.send(i18n.get(guild_id, "tracker.goodbye_discord", name=member.display_name))


async def setup(bot: commands.Bot) -> None:
    cog = TrackerCog(bot)
    await bot.add_cog(cog)
    cog.check_changes.start()
    cog.send_batched_report.start()
    cog.clan_member_check.start()
    cog.auto_report.start()