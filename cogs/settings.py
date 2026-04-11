import discord
from discord.ext import commands
import utils.i18n as i18n
import logging

log = logging.getLogger(__name__)

class SettingsCog(commands.Cog, name="Settings"):
    """Server settings and language management module."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="language", aliases=["dil"])
    @commands.has_permissions(administrator=True)
    async def language(self, ctx: commands.Context, lang: str = None) -> None:
        """
        Changes the server's language preference. (Admin only)
        Usage: !language en | !language tr
        """
        def t(key, **kw): return i18n.get(ctx.guild.id, key, **kw)

        if lang is None:
            current_lang = i18n.get_guild_language(ctx.guild.id)
            await ctx.send(t("settings.current_lang", lang=current_lang))
            return

        lang = lang.lower()
        if lang not in ["en", "tr"]:
            await ctx.send(t("settings.invalid_lang"))
            return

        # Update DB
        await self.bot.db.set_guild_language(ctx.guild.id, lang)
        # Update Cache
        i18n.set_guild_language(ctx.guild.id, lang)

        # Let the confirmation be localized based on the NEW language
        def t_new(key, **kw): return i18n.get(ctx.guild.id, key, **kw)
        await ctx.send(t_new("settings.lang_set"))

        log.info("Guild %s (ID: %s) changed language to %s", ctx.guild.name, ctx.guild.id, lang)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))

