import asyncio
import json
import os
import logging
import discord
from discord.ext import commands

from utils.config import LIDER_ROLE_ID
import utils.i18n as i18n

log = logging.getLogger(__name__)

class AuthCog(commands.Cog, name="Auth"):
    """Authorization and access control module."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data_path = "data/authorized_users.json"
        self._lock = asyncio.Lock()  # JSON concurrency protection
        self.authorized_users = self._load_authorized_users()
        
        # Add global bot check
        @bot.check
        async def global_auth_check(ctx: commands.Context):
            # Admin or Leader role check (Role ID based - spoofing protection)
            is_admin_or_leader = False
            if isinstance(ctx.author, discord.Member):
                is_admin_or_leader = (
                    ctx.author.guild_permissions.administrator or
                    (LIDER_ROLE_ID > 0 and any(role.id == LIDER_ROLE_ID for role in ctx.author.roles))
                )
            
            # Authorized user list check (from JSON)
            is_authorized = ctx.author.id in self.authorized_users
            
            # Authorization management commands can only be used by "Admin/Leader"
            if ctx.command.name in ["grant_auth", "revoke_auth", "yetki_ver", "yetki_al"]:
                return is_admin_or_leader
            
            # All other commands require Admin/Leader or Authorized status
            return is_admin_or_leader or is_authorized

    def _load_authorized_users(self) -> list[int]:
        if not os.path.exists(self.data_path):
            return []
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_authorized_users(self) -> None:
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.authorized_users, f)

    @commands.command(name="grant_auth", aliases=["yetki_ver"])
    async def grant_auth(self, ctx: commands.Context, member: discord.Member) -> None:
        """Grants bot usage authorization to the specified user. (Leader only)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if member.id in self.authorized_users:
            await ctx.send(t("auth.already_authorized", member=member.mention))
            return

        async with self._lock:
            self.authorized_users.append(member.id)
            self._save_authorized_users()
        await ctx.send(t("auth.granted", member=member.mention))
        log.info("Authorization granted: %s (ID: %s)", member.display_name, member.id)

    @commands.command(name="revoke_auth", aliases=["yetki_al"])
    async def revoke_auth(self, ctx: commands.Context, member: discord.Member) -> None:
        """Revokes bot usage authorization from the specified user. (Leader only)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if member.id not in self.authorized_users:
            await ctx.send(t("auth.not_authorized", member=member.mention))
            return

        async with self._lock:
            self.authorized_users.remove(member.id)
            self._save_authorized_users()
        await ctx.send(t("auth.revoked", member=member.mention))
        log.info("Authorization revoked: %s (ID: %s)", member.display_name, member.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global authorization error catcher."""
        if isinstance(error, commands.CheckFailure):
            # If this is not a subcommand error (doesn't have its own error handler), send message
            if not ctx.command.has_error_handler():
                guild_id = ctx.guild.id if ctx.guild else 0
                await ctx.send(i18n.get(guild_id, "auth.no_permission"))

    @grant_auth.error
    @revoke_auth.error
    async def auth_error(self, ctx: commands.Context, error: Exception):
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(t("auth.usage_error"))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(t("auth.member_not_found"))
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(t("auth.leader_only"))

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AuthCog(bot))

