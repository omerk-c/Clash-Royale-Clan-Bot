"""
Channel Manager Cog – Assign and manage notification channels via commands.

Commands:
  !set_channel <type> #channel  → Assigns a channel for a notification type
  !remove_channel <type>        → Removes assignment (reverts to default)
  !list_channels                → Shows all channel assignments
  !test_channel <type>          → Sends a test message to the specified channel
"""
import logging

import discord
from discord.ext import commands

from utils.channels import (
    CHANNEL_TYPES,
    set_channel,
    remove_channel,
    get_all_channels,
    get_notification_channel,
)
from utils.config import CHANNEL_ID
import utils.i18n as i18n

log = logging.getLogger(__name__)


class ChannelManagerCog(commands.Cog, name="Channel Manager"):
    """Notification channel assignment and management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── !set_channel command ───────────────────────────────────────────

    @commands.command(name="set_channel", aliases=["kanal_ayar"])
    @commands.has_permissions(administrator=True)
    async def set_channel(
        self, ctx: commands.Context, channel_type: str = None,
        channel: discord.TextChannel = None
    ) -> None:
        """Assigns a channel for a notification type."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if not channel_type or not channel:
            # Show help
            types_text = "\n".join(
                f"  `{key}` → {info['emoji']} {info['name']} – {info['description']}"
                for key, info in CHANNEL_TYPES.items()
            )
            await ctx.send(t("channel.usage_set", types_text=types_text))
            return

        channel_type = channel_type.lower()

        if channel_type not in CHANNEL_TYPES:
            valid = ", ".join(f"`{k}`" for k in CHANNEL_TYPES.keys())
            await ctx.send(t("channel.invalid_type", type=channel_type, valid=valid))
            return

        # Assign the channel
        success = set_channel(channel_type, channel.id)
        if success:
            info = CHANNEL_TYPES[channel_type]
            embed = discord.Embed(
                title=t("channel.set_success_title"),
                description=t("channel.set_success_desc", emoji=info['emoji'], name=info['name'], channel_mention=channel.mention),
                color=0x2ECC71,
            )
            embed.add_field(
                name=t("channel.type_field"),
                value=t("channel.type_desc", type=channel_type, desc=info['description']),
                inline=False,
            )
            await ctx.send(embed=embed)
            log.info(
                "Channel assigned: %s → #%s (ID: %s)",
                channel_type, channel.name, channel.id
            )
        else:
            await ctx.send(t("channel.set_failed"))

    # ── !remove_channel command ─────────────────────────────────────────

    @commands.command(name="remove_channel", aliases=["kanal_kaldir", "kanal_kaldır"])
    @commands.has_permissions(administrator=True)
    async def remove_channel(
        self, ctx: commands.Context, channel_type: str = None
    ) -> None:
        """Removes channel assignment, reverts to default channel."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if not channel_type:
            await ctx.send(t("channel.usage_remove"))
            return

        channel_type = channel_type.lower()

        if channel_type not in CHANNEL_TYPES:
            valid = ", ".join(f"`{k}`" for k in CHANNEL_TYPES.keys())
            await ctx.send(t("channel.invalid_type", type=channel_type, valid=valid))
            return

        if channel_type == "main":
            await ctx.send(t("channel.main_cannot_remove"))
            return

        success = remove_channel(channel_type)
        if success:
            info = CHANNEL_TYPES[channel_type]
            await ctx.send(t("channel.removed", emoji=info['emoji'], name=info['name']))
            log.info("Channel assignment removed: %s", channel_type)
        else:
            await ctx.send(t("channel.remove_failed"))

    # ── !list_channels command ──────────────────────────────────────────

    @commands.command(name="list_channels", aliases=["kanal_liste"])
    async def list_channels(self, ctx: commands.Context) -> None:
        """Shows all channel assignments (!list_channels)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        channels = get_all_channels()

        embed = discord.Embed(
            title=t("channel.list_title"),
            description=t("channel.list_desc"),
            color=0x3498DB,
        )

        for channel_type, info in CHANNEL_TYPES.items():
            channel_id = channels.get(channel_type)

            if channel_id:
                channel_obj = self.bot.get_channel(int(channel_id))
                if channel_obj:
                    status = f"✅ {channel_obj.mention}"
                else:
                    status = t("channel.channel_not_found", id=channel_id)
            else:
                if channel_type == "main":
                    default_ch = self.bot.get_channel(CHANNEL_ID)
                    if default_ch:
                        status = t("channel.default_env", mention=default_ch.mention)
                    else:
                        status = t("channel.default_env_id", id=CHANNEL_ID)
                else:
                    status = t("channel.not_assigned")

            embed.add_field(
                name=f"{info['emoji']} {info['name']} (`{channel_type}`)",
                value=f"{status}\n{info['description']}",
                inline=False,
            )

        embed.set_footer(text=t("channel.list_footer"))

        await ctx.send(embed=embed)

    # ── !test_channel command ───────────────────────────────────────────

    @commands.command(name="test_channel", aliases=["kanal_test"])
    @commands.has_permissions(administrator=True)
    async def test_channel(
        self, ctx: commands.Context, channel_type: str = None
    ) -> None:
        """Sends a test message to the specified notification channel."""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if not channel_type:
            await ctx.send(t("channel.usage_test"))
            return

        channel_type = channel_type.lower()

        if channel_type == "all":
            sent = 0
            for ctype, info in CHANNEL_TYPES.items():
                channel = await get_notification_channel(self.bot, ctype, CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title=t("channel.test_title", emoji=info['emoji'], name=info['name']),
                        description=t("channel.test_desc", type=ctype, desc=info['description']),
                        color=0x95A5A6,
                    )
                    await channel.send(embed=embed)
                    sent += 1

            await ctx.send(t("channel.test_all_success", count=sent))
            return

        if channel_type not in CHANNEL_TYPES:
            valid = ", ".join(f"`{k}`" for k in CHANNEL_TYPES.keys())
            await ctx.send(t("channel.invalid_type_test", valid=valid))
            return

        channel = await get_notification_channel(self.bot, channel_type, CHANNEL_ID)
        if channel is None:
            await ctx.send(t("channel.channel_not_found_test"))
            return

        info = CHANNEL_TYPES[channel_type]
        embed = discord.Embed(
            title=t("channel.test_title", emoji=info['emoji'], name=info['name']),
            description=t("channel.test_desc_specific", type=channel_type, desc=info['description']),
            color=0x95A5A6,
        )
        await channel.send(embed=embed)
        await ctx.send(t("channel.test_success", channel=channel.mention))

    # ── Error Handling ────────────────────────────────────────────────

    @set_channel.error
    @remove_channel.error
    @test_channel.error
    async def channel_error(self, ctx: commands.Context, error: Exception) -> None:
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(t("channel.err_admin"))
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(t("channel.err_not_found"))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(t("channel.err_missing"))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChannelManagerCog(bot))