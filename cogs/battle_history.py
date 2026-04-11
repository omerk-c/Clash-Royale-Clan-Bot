"""
Battle History Cog – Detailed analysis of player's last 25 battles.

Commands:
  !battle_history #TAG  → Detail of last 25 battles
  !deck_analysis #TAG   → Most used cards and deck analysis

Information Shown:
  - Win rate
  - Last 25 battle results (win/loss streak)
  - Game mode distribution
  - Most used cards
  - Average crowns
  - Least successful card/archetype
"""
import logging
from collections import Counter
from typing import Optional

import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
from utils.config import encode_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)


def _get_battle_result(battle: dict, player_tag: str) -> str:
    """Determines battle result: 'win', 'loss', 'draw'."""
    team = battle.get("team", [{}])
    opponent = battle.get("opponent", [{}])

    if not team or not opponent:
        return "draw"

    team_crowns = team[0].get("crowns", 0) if team else 0
    opp_crowns = opponent[0].get("crowns", 0) if opponent else 0

    if team_crowns > opp_crowns:
        return "win"
    elif team_crowns < opp_crowns:
        return "loss"
    return "draw"


def _result_emoji(result: str) -> str:
    """Result emoji."""
    return {"win": "🟢", "loss": "🔴", "draw": "🟡"}.get(result, "⚪")


def _calculate_streaks(results: list[str]) -> tuple[int, int]:
    """Calculates longest win and loss streaks."""
    max_win_streak = 0
    max_loss_streak = 0
    current_win = 0
    current_loss = 0

    for r in results:
        if r == "win":
            current_win += 1
            current_loss = 0
            max_win_streak = max(max_win_streak, current_win)
        elif r == "loss":
            current_loss += 1
            current_win = 0
            max_loss_streak = max(max_loss_streak, current_loss)
        else:
            current_win = 0
            current_loss = 0

    return max_win_streak, max_loss_streak


class BattleHistoryCog(commands.Cog, name="Battle History"):
    """Player battle history analysis."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    # ── !battle_history command ──────────────────────────────────────

    @commands.command(name="battle_history", aliases=["savas_gecmisi", "savaş_geçmişi"])
    async def battle_history_cmd(self, ctx: commands.Context, player_tag: str = None) -> None:
        """
        Detailed analysis of the player's last 25 battles.

        Usage:
          !battle_history #TAG  → Specified player
          !battle_history       → Linked account (if any)
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        # ── Determine tag ────────────────────────────────────────────
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
                await ctx.send(t("battle_history.no_account"))
                return

        if not player_tag.startswith("#"):
            player_tag = f"#{player_tag}"

        async with ctx.typing():
            # ── Fetch battle log from API ────────────────────────────
            battles = await self.api.get_player_battle_log(player_tag)
            if not battles:
                await ctx.send(t("battle_history.no_battles", tag=player_tag))
                return

            player_name = "Unknown"
            if battles and battles[0].get("team"):
                team_data = battles[0]["team"]
                if team_data:
                    player_name = team_data[0].get("name", "Unknown")

            # ── Analyze battle results ───────────────────────────────
            results: list[str] = []
            game_modes: Counter = Counter()
            card_usage: Counter = Counter()
            total_crowns = 0
            total_opp_crowns = 0
            battle_details: list[dict] = []

            for battle in battles:
                result = _get_battle_result(battle, player_tag)
                results.append(result)

                # Game mode
                game_mode = battle.get("gameMode", {}).get("name", "Unknown")
                game_mode_localized = t(f"battle_history.game_modes.{game_mode}", default=game_mode)
                game_modes[game_mode_localized] += 1

                # Crown count
                team = battle.get("team", [{}])
                opponent = battle.get("opponent", [{}])
                t_crowns = team[0].get("crowns", 0) if team else 0
                o_crowns = opponent[0].get("crowns", 0) if opponent else 0
                total_crowns += t_crowns
                total_opp_crowns += o_crowns

                # Used cards
                if team and team[0].get("cards"):
                    for card in team[0]["cards"]:
                        card_name = card.get("name", "Unknown")
                        card_usage[card_name] += 1

                # Detail info (last 10)
                if len(battle_details) < 10:
                    battle_type = battle.get("type", "?")
                    arena = battle.get("arena", {}).get("name", "?")

                    opp_name = "?"
                    if opponent and opponent[0]:
                        opp_name = opponent[0].get("name", "?")

                    battle_details.append({
                        "result": result,
                        "mode": game_mode_localized,
                        "crowns": f"{t_crowns}-{o_crowns}",
                        "opponent": opp_name,
                        "type": battle_type,
                        "arena": arena,
                    })

            # ── Statistics ───────────────────────────────────────────
            total = len(results)
            wins = results.count("win")
            losses = results.count("loss")
            draws = results.count("draw")
            win_rate = (wins / total * 100) if total > 0 else 0
            avg_crowns = total_crowns / max(total, 1)
            avg_opp_crowns = total_opp_crowns / max(total, 1)
            win_streak, loss_streak = _calculate_streaks(results)

            # ── Create Embed ─────────────────────────────────────────
            embed = discord.Embed(
                title=t("battle_history.title", name=player_name),
                description=t("battle_history.desc", tag=player_tag, total=total),
                color=0xE74C3C,
            )

            # Win rate bar
            wr_filled = int(win_rate / 5)
            wr_bar = "█" * wr_filled + "░" * (20 - wr_filled)

            embed.add_field(
                name=t("battle_history.stats.title"),
                value=t("battle_history.stats.value", bar=wr_bar, win_rate=win_rate, wins=wins, losses=losses, draws=draws, win_streak=win_streak, loss_streak=loss_streak, avg_crowns=avg_crowns, avg_opp_crowns=avg_opp_crowns),
                inline=False,
            )

            # ── Last 10 Battle Results ──────────────────────────────
            result_line = " ".join(_result_emoji(r) for r in results[:10])
            embed.add_field(
                name=t("battle_history.recent.title"),
                value=result_line,
                inline=False,
            )

            # ── Last 10 Battle Details ──────────────────────────────
            detail_lines = []
            for i, d in enumerate(battle_details, 1):
                emoji = _result_emoji(d["result"])
                detail_lines.append(
                    f"{emoji} **{d['crowns']}** vs {d['opponent'][:12]} · {d['mode']}"
                )

            if detail_lines:
                embed.add_field(
                    name=t("battle_history.details.title"),
                    value="\n".join(detail_lines),
                    inline=False,
                )

            # ── Game Mode Distribution ──────────────────────────────
            mode_lines = []
            for mode, count in game_modes.most_common(5):
                pct = count / total * 100
                mode_lines.append(t("battle_history.modes.line", mode=mode, count=count, pct=pct))
            if mode_lines:
                embed.add_field(
                    name=t("battle_history.modes.title"),
                    value="\n".join(mode_lines),
                    inline=True,
                )

            # ── Most Used Cards ──────────────────────────────────────
            top_cards = card_usage.most_common(8)
            if top_cards:
                card_lines = []
                for card_name, count in top_cards:
                    pct = count / total * 100
                    card_lines.append(t("battle_history.cards.line", card=card_name, count=count, pct=pct))
                embed.add_field(
                    name=t("battle_history.cards.title"),
                    value="\n".join(card_lines),
                    inline=True,
                )

            embed.set_footer(
                text=t("battle_history.footer")
            )

        await ctx.send(embed=embed)

    # ── !deck_analysis command ───────────────────────────────────────

    @commands.command(name="deck_analysis", aliases=["deste_analiz"])
    async def deck_analysis_cmd(self, ctx: commands.Context, player_tag: str = None) -> None:
        """
        Player deck usage analysis.

        Usage:
          !deck_analysis #TAG  → Specified player
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if not player_tag:
            await ctx.send(t("battle_history.deck_analysis.usage"))
            return

        if not player_tag.startswith("#"):
            player_tag = f"#{player_tag}"

        async with ctx.typing():
            battles = await self.api.get_player_battle_log(player_tag)
            if not battles:
                await ctx.send(t("battle_history.no_battles", tag=player_tag))
                return

            player_name = "Unknown"
            if battles and battles[0].get("team"):
                team_data = battles[0]["team"]
                if team_data:
                    player_name = team_data[0].get("name", "Unknown")

            # ── Deck analysis ────────────────────────────────────────
            deck_counter: Counter = Counter()
            card_win_rate: dict[str, dict] = {}  # {card_name: {"wins": N, "total": N}}
            elixir_costs: list[float] = []

            for battle in battles:
                result = _get_battle_result(battle, player_tag)
                team = battle.get("team", [{}])
                if not team or not team[0].get("cards"):
                    continue

                cards = team[0]["cards"]
                card_names = sorted(c.get("name", "?") for c in cards)
                deck_key = " | ".join(card_names)
                deck_counter[deck_key] += 1

                # Calculate elixir cost
                total_elixir = sum(c.get("elixirCost", 0) for c in cards if c.get("elixirCost"))
                if total_elixir > 0:
                    avg_elixir = total_elixir / len([c for c in cards if c.get("elixirCost")])
                    elixir_costs.append(avg_elixir)

                # Card-based win rate
                for card in cards:
                    cname = card.get("name", "?")
                    if cname not in card_win_rate:
                        card_win_rate[cname] = {"wins": 0, "total": 0}
                    card_win_rate[cname]["total"] += 1
                    if result == "win":
                        card_win_rate[cname]["wins"] += 1

            # ── Create Embed ─────────────────────────────────────────
            embed = discord.Embed(
                title=t("battle_history.deck_analysis.title", name=player_name),
                description=t("battle_history.deck_analysis.desc", tag=player_tag, count=len(battles)),
                color=0x9B59B6,
            )

            # ── Most Used Decks ──────────────────────────────────────
            top_decks = deck_counter.most_common(3)
            for i, (deck, count) in enumerate(top_decks, 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                cards_list = deck.split(" | ")
                cards_formatted = "\n".join(f"  • {c}" for c in cards_list)
                embed.add_field(
                    name=t("battle_history.deck_analysis.top_decks", medal=medal, index=i, count=count),
                    value=cards_formatted,
                    inline=False,
                )

            # ── Card-Based Win Rate ──────────────────────────────────
            sorted_cards = sorted(
                card_win_rate.items(),
                key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                reverse=True,
            )

            # Best cards
            best_lines = []
            for cname, stats in sorted_cards[:5]:
                wr = stats["wins"] / max(stats["total"], 1) * 100
                best_lines.append(
                    t("battle_history.deck_analysis.best_line", card=cname, wr=wr, wins=stats['wins'], total=stats['total'])
                )
            if best_lines:
                embed.add_field(
                    name=t("battle_history.deck_analysis.best_cards"),
                    value="\n".join(best_lines),
                    inline=True,
                )

            # Worst cards
            worst_lines = []
            for cname, stats in sorted_cards[-5:]:
                if stats["total"] >= 2:  # Used at least twice
                    wr = stats["wins"] / max(stats["total"], 1) * 100
                    worst_lines.append(
                        t("battle_history.deck_analysis.worst_line", card=cname, wr=wr, wins=stats['wins'], total=stats['total'])
                    )
            if worst_lines:
                embed.add_field(
                    name=t("battle_history.deck_analysis.worst_cards"),
                    value="\n".join(worst_lines),
                    inline=True,
                )

            # ── Average Elixir ───────────────────────────────────────
            if elixir_costs:
                avg_elixir = sum(elixir_costs) / len(elixir_costs)
                embed.add_field(
                    name=t("battle_history.deck_analysis.avg_elixir.title"),
                    value=t("battle_history.deck_analysis.avg_elixir.value", avg=avg_elixir),
                    inline=True,
                )

            embed.set_footer(text=t("battle_history.deck_analysis.footer"))

        await ctx.send(embed=embed)

    @battle_history_cmd.error
    @deck_analysis_cmd.error
    async def battle_error(self, ctx: commands.Context, error: Exception) -> None:
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(t("battle_history.error"))
            log.exception("Battle history error: %s", error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleHistoryCog(bot))