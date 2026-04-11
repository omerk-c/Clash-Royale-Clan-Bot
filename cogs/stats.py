"""
Stats Cog – Visual war history graph and player performance table.
Prefix commands (!graph, !player_board).

!graph        → Line graph with matplotlib for clan fame
!player_board → Player's weekly war score table (Embed)
"""
import asyncio
import io
import logging

import discord
from discord.ext import commands

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.cr_api import ClashRoyaleAPI
from utils.config import CLAN_TAG, clean_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)

# ── Graphics color palette (Discord dark mode compatible) ─────────────────────
DARK_BG = "#2C2F33"
DARKER_BG = "#23272A"
GRID_COLOR = "#40444B"
CLAN_COLORS = ["#FFA500", "#00BFFF", "#FF6384", "#36D399", "#C084FC"]
TEXT_COLOR = "#DCDDDE"

MAX_WEEKS = 10


def _extract_clan_fame_from_riverlog(
    warlog: dict | None, clan_tag: str
) -> list[int]:
    """
    Extracts weekly fame values from a clan's river race log.
    Tag comparison is done by stripping the # sign.
    """
    if not warlog or "items" not in warlog:
        return []

    scores: list[int] = []
    raw_tag = clean_tag(clan_tag)

    for item in warlog["items"][:MAX_WEEKS]:
        standings = item.get("standings", [])
        for s in standings:
            clan = s.get("clan", {})
            api_tag = clean_tag(clan.get("tag", ""))
            if api_tag == raw_tag:
                fame = clan.get("fame", 0)
                if fame == 0:
                    participants = clan.get("participants", [])
                    if isinstance(participants, list):
                        fame = sum(p.get("fame", 0) for p in participants)
                scores.append(fame)
                break

    scores.reverse()
    return scores


def _build_chart(
    clan_data: list[tuple[str, str, list[int]]],
    our_tag: str,
    lang_dict: dict[str, str],
) -> io.BytesIO:
    """Creates a matplotlib line graph and returns it as BytesIO."""
    fig, ax = plt.subplots(figsize=(12, 6))

    fig.patch.set_facecolor(DARKER_BG)
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.6)
    
    x_label = lang_dict.get("graph_x", "Week")
    y_label = lang_dict.get("graph_y", "Points")
    plot_title = lang_dict.get("graph_plot_title", "⚔️ Clan War Point History")
    
    ax.set_xlabel(x_label, color=TEXT_COLOR, fontsize=11)
    ax.set_ylabel(y_label, color=TEXT_COLOR, fontsize=11)
    ax.set_title(plot_title, color=TEXT_COLOR, fontsize=14, pad=15)

    max_weeks = max((len(scores) for _, _, scores in clan_data), default=0)

    our_tag_clean = clean_tag(our_tag)

    for idx, (tag, name, scores) in enumerate(clan_data):
        if not scores:
            continue
        color = CLAN_COLORS[idx % len(CLAN_COLORS)]
        weeks = list(range(1, len(scores) + 1))
        is_ours = clean_tag(tag) == our_tag_clean

        ax.plot(
            weeks,
            scores,
            marker="o",
            markersize=6 if is_ours else 4,
            linewidth=3 if is_ours else 1.8,
            color=color,
            label=f"{'⭐ ' if is_ours else ''}{name}",
            alpha=1.0 if is_ours else 0.7,
            zorder=10 if is_ours else 5,
        )

        if is_ours:
            for w, s in zip(weeks, scores):
                ax.annotate(
                    f"{s:,}",
                    (w, s),
                    textcoords="offset points",
                    xytext=(0, 10),
                    fontsize=7,
                    color=color,
                    ha="center",
                )

    if max_weeks > 0:
        ax.set_xticks(range(1, max_weeks + 1))
        ax.set_xticklabels([f"{x_label[:1]}{i}" for i in range(1, max_weeks + 1)])

    ax.legend(
        loc="upper left",
        fontsize=9,
        facecolor=DARKER_BG,
        edgecolor=GRID_COLOR,
        labelcolor=TEXT_COLOR,
    )
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return buf


class StatsCog(commands.Cog, name="Stats"):
    """Visual war statistics and player performance table."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    # ── !graph ───────────────────────────────────────────────────────

    @commands.command(name="graph", aliases=["grafik"])
    async def graph_cmd(self, ctx: commands.Context) -> None:
        """Clan and opponent fame history graph (!graph)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        msg = await ctx.send(t("stats.graph_preparing"))

        race = await self.api.get_current_river_race()
        if not race or "clans" not in race:
            await msg.edit(content=t("stats.no_active_race"))
            return

        race_clans = race["clans"]
        tags = [c["tag"] for c in race_clans]
        names = {c["tag"]: c.get("name", "?") for c in race_clans}

        warlog_tasks = [self.api.get_river_race_log_for(tag) for tag in tags]
        warlogs = await asyncio.gather(*warlog_tasks)

        clan_data: list[tuple[str, str, list[int]]] = []
        for tag, warlog in zip(tags, warlogs):
            fame_history = _extract_clan_fame_from_riverlog(warlog, tag)

            clan_data.append((tag, names.get(tag, "?"), fame_history))

        our_tag_clean = clean_tag(CLAN_TAG)
        clan_data.sort(key=lambda c: clean_tag(c[0]) != our_tag_clean)

        if not any(scores for _, _, scores in clan_data):
            await msg.edit(content=t("stats.no_clan_data"))
            return

        lang_dict = {
            "graph_x": t("stats.graph_x"),
            "graph_y": t("stats.graph_y"),
            "graph_plot_title": t("stats.graph_plot_title")
        }

        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, _build_chart, clan_data, CLAN_TAG, lang_dict) # type: ignore

        file = discord.File(buf, filename="clan_war_graph.png")
        embed = discord.Embed(
            title=t("stats.graph_title"),
            description=t("stats.graph_desc", weeks=MAX_WEEKS),
            color=0x3498DB,
        )
        embed.set_image(url="attachment://clan_war_graph.png")
        await msg.delete()
        await ctx.send(embed=embed, file=file)

    # ── !player_board ─────────────────────────────────────────────────

    @commands.command(name="player_board", aliases=["oyuncu_tablo"])
    async def player_board_cmd(
        self, ctx: commands.Context, player_tag: str = None
    ) -> None:
        """Player weekly war performance table (!player_board or !player_board #TAG)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            race = await self.api.get_current_river_race()
            if not race or "clan" not in race:
                await ctx.send(t("stats.board_fetch_error"))
                return

            if player_tag:
                if not player_tag.startswith("#"):
                    player_tag = f"#{player_tag}"

                participants = race["clan"].get("participants", [])
                target_player = None
                for p in participants:
                    if clean_tag(p.get("tag", "")) == clean_tag(player_tag):
                        target_player = p
                        break

                if not target_player:
                    await ctx.send(t("stats.board_player_not_found", tag=player_tag))
                    return

                name = target_player.get("name", "Unknown")
                fame = target_player.get("fame", 0)
                decks_used = target_player.get("decksUsed", 0)
                decks_today = target_player.get("decksUsedToday", 0)
                boat_attacks = target_player.get("boatAttacks", 0)
                repair_points = target_player.get("repairPoints", 0)

                embed = discord.Embed(
                    title=t("stats.board_player_title", name=name),
                    color=0xF1C40F,
                )

                today_progress = min(int((decks_today / 4) * 20), 20)
                today_bar = "█" * today_progress + "░" * (20 - today_progress)

                embed.description = t(
                    "stats.board_player_desc",
                    fame=f"{fame:,}",
                    total=decks_used,
                    today=decks_today,
                    bar=today_bar,
                    boat=boat_attacks,
                    repair=repair_points
                )

                await ctx.send(embed=embed)
                return

            participants = race["clan"].get("participants", [])

            if not participants:
                await ctx.send(t("stats.board_no_participants"))
                return

            sorted_participants = sorted(
                participants, key=lambda p: p.get("fame", 0), reverse=True
            )

            embed = discord.Embed(
                title=t("stats.board_clan_title"),
                color=0xE67E22,
            )

            max_decks = max(
                (p.get("decksUsed", 0) for p in participants), default=4
            )
            max_decks = max(max_decks, 1)

            lines = []
            for i, p in enumerate(sorted_participants[:15], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                name = p.get("name", "Unknown")[:15]
                fame = p.get("fame", 0)
                decks_used = p.get("decksUsed", 0)
                decks_today = p.get("decksUsedToday", 0)

                progress = min(int((decks_used / max_decks) * 10), 10)
                bar = "█" * progress + "░" * (10 - progress)

                lines.append(t("stats.board_clan_line", medal=medal, name=name, fame=f"{fame:,}", bar=bar, used=decks_used, today=decks_today))

            embed.description = "\n".join(lines)
            embed.set_footer(text=t("stats.board_clan_footer", count=len(sorted_participants)))

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCog(bot))