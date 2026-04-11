"""
Donations Cog – Tracks donation leaderboards and leechers.
"""
import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
import utils.i18n as i18n


class DonationsCog(commands.Cog, name="Donations"):
    """Commands related to card donations."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    @commands.command(name="donations", aliases=["bagis"])
    async def donations(self, ctx: commands.Context) -> None:
        """Shows the clan donation leaderboard (!donations)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("donations.fetch_failed"))
                return

            sorted_m = sorted(members, key=lambda m: m.get("donations", 0), reverse=True)

            embed = discord.Embed(title=t("donations.rank_title"), color=0x2ECC71)
            lines = []
            for i, m in enumerate(sorted_m[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                don = m.get("donations", 0)
                rec = m.get("donationsReceived", 0)
                lines.append(t("donations.rank_line", medal=medal, name=m['name'], donations=don, received=rec))
            embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @commands.command(name="leechers", aliases=["somuruculer", "sömürücüler"])
    async def leechers(self, ctx: commands.Context) -> None:
        """Shows members who donate below the clan average but receive more (!leechers)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            members = await self.api.get_clan_members()
            if not members:
                await ctx.send(t("donations.fetch_failed"))
                return

            total_donations = sum(m.get("donations", 0) for m in members)
            avg_donations = total_donations / max(len(members), 1)
            threshold = avg_donations * 0.20

            leechers: list[dict] = []
            for m in members:
                donated = m.get("donations", 0)
                received = m.get("donationsReceived", 0)
                if donated < threshold and received > avg_donations:
                    leechers.append(m)

            if not leechers:
                await ctx.send(t("donations.no_leechers"))
                return

            leechers.sort(key=lambda m: m.get("donationsReceived", 0), reverse=True)

            embed = discord.Embed(
                title=t("donations.leecher_title"),
                description=t("donations.leecher_desc", avg=avg_donations, threshold=threshold),
                color=0xE74C3C,
            )

            lines = []
            for m in leechers[:15]:
                don = m.get("donations", 0)
                rec = m.get("donationsReceived", 0)
                ratio = rec / max(don, 1)
                lines.append(t("donations.leecher_line", name=m['name'], don=don, rec=rec, ratio=ratio))
            embed.add_field(name=t("donations.leecher_field"), value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DonationsCog(bot))
