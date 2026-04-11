"""
War Cog – Clan info, river race, contribution ranking, warlog, and war reminder.
War reminder is routed to the "war" channel.
"""
import json
import logging
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import CHANNEL_ID, CLAN_TAG, clean_tag
from utils.channels import get_notification_channel
import utils.i18n as i18n

log = logging.getLogger(__name__)

LINKED_ACCOUNTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "linked_accounts.json"
)


def _load_linked_accounts() -> dict[str, str]:
    try:
        with open(LINKED_ACCOUNTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _calculate_clan_decks(clan_data: dict) -> tuple[int, int, int]:
    participants = clan_data.get("participants", [])
    total_used = sum(p.get("decksUsed", 0) for p in participants)
    total_today = sum(p.get("decksUsedToday", 0) for p in participants)
    active = sum(1 for p in participants if p.get("decksUsed", 0) > 0)
    return total_used, total_today, active


def _calculate_clan_fame(clan_data: dict) -> int:
    fame = clan_data.get("fame", 0)
    if fame == 0:
        fame = clan_data.get("periodPoints", 0)
    if fame == 0:
        participants = clan_data.get("participants", [])
        fame = sum(p.get("fame", 0) for p in participants)
    return fame


class WarCog(commands.Cog, name="War"):
    """Clan war and river race commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    def cog_unload(self) -> None:
        self.war_reminder.cancel()

    @commands.command(name="clan", aliases=["klan"])
    async def clan_cmd(self, ctx: commands.Context) -> None:
        """Shows general clan info (!clan)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            clan = await self.api.get_clan_info()
            if not clan:
                await ctx.send(t("war.fetch_error"))
                return

            embed = discord.Embed(
                title=t("war.clan_title", name=clan['name']),
                color=0x1ABC9C,
            )
            embed.set_thumbnail(url=clan.get("badgeUrls", {}).get("medium", ""))
            embed.add_field(name=t("war.trophies"), value=f"{clan.get('clanScore', '?'):,}")
            embed.add_field(name=t("war.members"), value=f"{clan.get('members', '?')}/50")
            embed.add_field(name=t("war.war_wins"), value=f"{clan.get('warWins', 0)}")
            embed.add_field(name=t("war.clan_level"), value=clan.get("clanLevel", "?"))
            embed.add_field(
                name=t("war.description"),
                value=clan.get("description", t("war.none"))[:1024],
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name="wars", aliases=["savaslar"])
    async def wars_cmd(self, ctx: commands.Context) -> None:
        """Shows active river race status (!wars)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            race = await self.api.get_current_river_race()
            if not race:
                await ctx.send(t("war.race_fetch_error"))
                return
            if "clan" not in race:
                await ctx.send(t("war.no_clan_data"))
                return

            period_type = race.get("periodType", "")
            if period_type == "training":
                await ctx.send(t("war.training_days"))
                return

            clans = race.get("clans", [])
            if not clans:
                await ctx.send(t("war.no_clans_race"))
                return

            clan_scores = [(c, _calculate_clan_fame(c)) for c in clans]
            clan_scores.sort(key=lambda x: x[1], reverse=True)

            embed = discord.Embed(title=t("war.race_title"), color=0xE74C3C)

            period_index = race.get("periodIndex", "?")
            section_index = race.get("sectionIndex", "?")
            embed.set_author(
                name=t("war.race_period", section=section_index, period=period_index, type=period_type)
            )

            table = ""
            for i, (clan_data, fame) in enumerate(clan_scores[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                clan_name = clan_data.get("name", t("war.unknown"))
                total_decks, decks_today, active_count = _calculate_clan_decks(clan_data)

                our_clan = clean_tag(CLAN_TAG) == clean_tag(clan_data.get("tag", ""))
                if our_clan:
                    clan_name = f"⭐ {clan_name}"

                table += t("war.clan_score_line", medal=medal, name=clan_name, fame=f"{fame:,}", decks=total_decks, today=decks_today, active=active_count)

            embed.description = table
            embed.set_footer(text=t("war.footer_api"))
        await ctx.send(embed=embed)

    @commands.command(name="contribution", aliases=["katki", "katkı"])
    async def contribution_cmd(self, ctx: commands.Context) -> None:
        """River race contribution top 10 rank (!contribution)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            race = await self.api.get_current_river_race()
            if not race or "clan" not in race:
                await ctx.send(t("war.race_fetch_error"))
                return
            if race.get("periodType", "") == "training":
                await ctx.send(t("war.training_days"))
                return

            participants = race["clan"].get("participants", [])
            if not participants:
                await ctx.send(t("war.no_participants"))
                return

            sorted_p = sorted(participants, key=lambda p: p.get("fame", 0), reverse=True)
            embed = discord.Embed(title=t("war.contrib_title"), color=0xF1C40F)
            lines = []
            for i, p in enumerate(sorted_p[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                name = p.get("name", t("war.unknown"))
                fame = p.get("fame", 0)
                decks_used = p.get("decksUsed", 0)
                decks_today = p.get("decksUsedToday", 0)
                lines.append(t("war.contrib_line", medal=medal, name=name, fame=f"{fame:,}", used=decks_used, today=decks_today))
            embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @commands.command(name="warlog")
    async def warlog(self, ctx: commands.Context) -> None:
        """Shows the last 5 clan wars (!warlog)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            data = await self.api.get_river_race_log()
            if not data or "items" not in data:
                await ctx.send(t("war.warlog_fetch_error"))
                return

            embed = discord.Embed(title=t("war.warlog_title"), color=0x9B59B6)
            our_tag = clean_tag(CLAN_TAG)

            for war in data["items"][:5]:
                created_date = war.get("createdDate", "")
                if created_date:
                    try:
                        date_obj = datetime.strptime(created_date.split("T")[0], "%Y%m%d")
                        formatted_date = date_obj.strftime("%d.%m.%Y")
                    except Exception:
                        formatted_date = created_date[:10]
                else:
                    formatted_date = t("war.unknown")

                standings = war.get("standings", [])
                our_result = None
                for standing in standings:
                    clan_info = standing.get("clan", {})
                    if clean_tag(clan_info.get("tag", "")) == our_tag:
                        our_result = standing
                        break

                if our_result:
                    clan_info = our_result.get("clan", {})
                    fame = clan_info.get("fame", 0)
                    if fame == 0:
                        parts = clan_info.get("participants", [])
                        if isinstance(parts, list):
                            fame = sum(p.get("fame", 0) for p in parts)

                    rank = our_result.get("rank", "?")
                    trophy_change = our_result.get("trophyChange", 0)
                    raw_participants = clan_info.get("participants", [])
                    participant_count = len(raw_participants) if isinstance(raw_participants, list) else raw_participants
                    rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}.get(rank, f"#{rank}")

                    embed.add_field(
                        name=f"📅 {formatted_date}",
                        value=t("war.rank", emoji=rank_emoji, fame=f"{fame:,}", count=participant_count, trophy=trophy_change),
                        inline=True,
                    )
                else:
                    embed.add_field(name=f"📅 {formatted_date}", value=t("war.no_clan_data_date"), inline=True)

            embed.set_footer(text=t("war.warlog_footer"))
        await ctx.send(embed=embed)

    @commands.command(name="list", aliases=["liste"])
    async def list_cmd(self, ctx: commands.Context) -> None:
        """Lists clan members with their roles (!list)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("war.list_fetch_error"))
                return

            lines = []
            for m in members:
                name = m.get("name", t("war.unknown")).replace("`", "")
                
                raw_role = m.get("role", "member")
                role_key = "war.unknown"
                if raw_role == "member": role_key = "war.role_member"
                elif raw_role == "elder": role_key = "war.role_elder"
                elif raw_role == "coLeader": role_key = "war.role_co_leader"
                elif raw_role == "leader": role_key = "war.role_leader"
                
                role_tr = t(role_key)
                don = m.get("donations", 0)
                rec = m.get("donationsReceived", 0)
                lines.append(t("war.list_line", name=name, role=role_tr, don=don, rec=rec))

            embed = discord.Embed(title=t("war.list_title"), color=0x3498DB)
            text = "\n".join(lines)
            embed.description = text[:4093] + "..." if len(text) > 4096 else text
        await ctx.send(embed=embed)

    @commands.command(name="tags")
    async def tags_cmd(self, ctx: commands.Context) -> None:
        """Lists member names and Clash Royale tags (!tags)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("war.list_fetch_error"))
                return

            lines = []
            for i, m in enumerate(members, 1):
                name = m.get("name", t("war.unknown")).replace("`", "")
                tag = m.get("tag", "?")
                lines.append(t("war.tags_line", i=i, name=name, tag=tag))

            embed = discord.Embed(
                title=t("war.tags_title"),
                color=0x1ABC9C,
            )
            text = "\n".join(lines)
            if len(text) > 4096:
                embed.description = text[:4093] + "..."
            else:
                embed.description = text
            embed.set_footer(text=t("war.tags_footer", count=len(members)))
        await ctx.send(embed=embed)

    @commands.command(name="inactive", aliases=["katilmayanlar", "sıfırcılar", "sifircilar"])
    async def inactive_cmd(self, ctx: commands.Context) -> None:
        """Lists players who didn't participate (!inactive)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            race = await self.api.get_current_river_race()
            if not race or "clan" not in race:
                await ctx.send(t("war.race_fetch_error"))
                return
            if race.get("periodType", "") == "training":
                await ctx.send(t("war.training_days"))
                return

            participants = {p.get("tag"): p for p in race["clan"].get("participants", [])}
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("war.list_fetch_error"))
                return

            lazy_members = []
            for m in members:
                tag = m.get("tag")
                name = m.get("name", t("war.unknown")).replace("`", "")
                p_data = participants.get(tag)
                if not p_data or p_data.get("fame", 0) == 0:
                    lazy_members.append(f"• **{name}**")

            if not lazy_members:
                await ctx.send(t("war.all_participated"))
                return

            embed = discord.Embed(
                title=t("war.inactive_title"),
                description=t("war.inactive_desc", count=len(lazy_members)),
                color=0xE74C3C,
            )
            text = "\n".join(lazy_members)
            if len(embed.description + text) <= 4096:
                embed.description += text
            else:
                embed.description += text[:4000] + "\n..."
        await ctx.send(embed=embed)

    @commands.command(name="help", aliases=["yardim", "yardım"])
    async def help_cmd(self, ctx: commands.Context) -> None:
        """Lists all commands (!help)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        embed = discord.Embed(
            title=t("war.help_title"),
            description=t("war.help_prefix"),
            color=0x2E86C1,
        )
        embed.add_field(name=t("war.help_war"), value=t("war.help_war_val"), inline=False)
        embed.add_field(name=t("war.help_stats"), value=t("war.help_stats_val"), inline=False)
        embed.add_field(name=t("war.help_profile"), value=t("war.help_profile_val"), inline=False)
        embed.add_field(name=t("war.help_history"), value=t("war.help_history_val"), inline=False)
        embed.add_field(name=t("war.help_badges"), value=t("war.help_badges_val"), inline=False)
        embed.add_field(name=t("war.help_deck"), value=t("war.help_deck_val"), inline=False)
        embed.add_field(name=t("war.help_records"), value=t("war.help_records_val"), inline=False)
        embed.add_field(name=t("war.help_report"), value=t("war.help_report_val"), inline=False)
        embed.add_field(name=t("war.help_donations"), value=t("war.help_donations_val"), inline=False)
        embed.add_field(name=t("war.help_channels"), value=t("war.help_channels_val"), inline=False)
        embed.add_field(name=t("war.help_other"), value=t("war.help_other_val"), inline=False)
        await ctx.send(embed=embed)

    # ── War Reminder → war channel ─────────────────────────────

    @tasks.loop(minutes=30)
    async def war_reminder(self) -> None:
        channel = await get_notification_channel(self.bot, "war", CHANNEL_ID)
        if channel is None:
            return
            
        guild_id = channel.guild.id if hasattr(channel, "guild") else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)

        race = await self.api.get_current_river_race()
        if not race or "clan" not in race:
            return
        if race.get("periodType", "") != "warDay":
            return

        end_time_str = race.get("periodEndTime")
        if not end_time_str:
            return

        try:
            end_time = datetime.strptime(end_time_str, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return

        now = datetime.now(timezone.utc)
        remaining = (end_time - now).total_seconds()
        if remaining > 4 * 3600 or remaining < 0:
            return

        hours_left = remaining / 3600
        participants = race["clan"].get("participants", [])
        linked = _load_linked_accounts()

        lazy_players = []
        for p in participants:
            if p.get("decksUsed", 0) < 4:
                tag = p.get("tag", "")
                name = p.get("name", t("war.unknown"))
                discord_id = linked.get(tag)
                if discord_id:
                    lazy_players.append(f"<@{discord_id}> ({name})")
                else:
                    lazy_players.append(f"⚠️ {name} (`{tag}`)")

        if not lazy_players:
            return

        embed = discord.Embed(
            title=t("war.reminder_title"),
            description=t("war.reminder_desc", hours=f"{hours_left:.1f}"),
            color=0xE74C3C,
        )
        text = "\n".join(lazy_players)
        while text:
            chunk, text = text[:1024], text[1024:]
            embed.add_field(name="\u200b", value=chunk, inline=False)

        await channel.send(embed=embed)

    @war_reminder.before_loop
    async def before_war_reminder(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = WarCog(bot)
    await bot.add_cog(cog)
    cog.war_reminder.start()