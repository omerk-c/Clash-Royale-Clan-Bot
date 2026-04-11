"""
Prediction Cog – War outcome prediction using an advanced Normal Distribution model.
Prefix Command (!prediction)
"""
import asyncio
import logging
import math
from collections import defaultdict

import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
from utils.config import CLAN_TAG, clean_tag
import utils.i18n as i18n

log = logging.getLogger(__name__)

MAX_WAR_HISTORY = 10


def _normal_cdf(x: float) -> float:
    """Φ(x) – standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _extract_fame_history(warlog_data: dict | None, clan_tag: str) -> list[int]:
    """
    Extracts weekly fame history for the clan from the river race log.
    Tag comparison is done without the # sign.
    """
    if not warlog_data or "items" not in warlog_data:
        return []

    scores: list[int] = []
    raw_tag = clean_tag(clan_tag)

    for item in warlog_data["items"][:MAX_WAR_HISTORY]:
        standings = item.get("standings", [])
        for s in standings:
            clan = s.get("clan", {})
            api_tag = clean_tag(clan.get("tag", ""))
            if api_tag == raw_tag:
                fame = clan.get("fame", 0) or clan.get("score", 0)
                if fame == 0:
                    participants = clan.get("participants", [])
                    if isinstance(participants, list):
                        fame = sum(p.get("fame", 0) for p in participants)
                if fame > 0:
                    scores.append(fame)
                break
    return scores


def _compute_stats(scores: list[int]) -> tuple[float, float]:
    if not scores:
        return 5000.0, 2000.0

    n = len(scores)
    mu = sum(scores) / n
    if n < 2:
        return mu, mu * 0.25

    variance = sum((x - mu) ** 2 for x in scores) / (n - 1)
    sigma = max(variance**0.5, mu * 0.05)
    return mu, sigma


def _prob_a_beats_b(
    mu_a: float, sig_a: float, mu_b: float, sig_b: float
) -> float:
    diff_mu = mu_a - mu_b
    diff_sigma = math.sqrt(sig_a**2 + sig_b**2)
    if diff_sigma == 0:
        return 0.5
    return _normal_cdf(diff_mu / diff_sigma)


def _compute_rank_probabilities(
    clan_stats: list[tuple[str, str, float, float]],
) -> dict[str, list[float]]:
    n = len(clan_stats)
    tags = [c[0] for c in clan_stats]

    win_prob: dict[str, dict[str, float]] = defaultdict(dict)
    for i, (tag_i, _, mu_i, sig_i) in enumerate(clan_stats):
        for j, (tag_j, _, mu_j, sig_j) in enumerate(clan_stats):
            if i == j:
                win_prob[tag_i][tag_j] = 0.5
            else:
                win_prob[tag_i][tag_j] = _prob_a_beats_b(
                    mu_i, sig_i, mu_j, sig_j
                )

    from itertools import permutations

    rank_probs: dict[str, list[float]] = {tag: [0.0] * n for tag in tags}

    for perm in permutations(range(n)):
        prob = 1.0
        for rank_pos in range(n):
            for lower_rank_pos in range(rank_pos + 1, n):
                winner_tag = tags[perm[rank_pos]]
                loser_tag = tags[perm[lower_rank_pos]]
                prob *= win_prob[winner_tag][loser_tag]

        for rank_pos, clan_idx in enumerate(perm):
            rank_probs[tags[clan_idx]][rank_pos] += prob

    for tag in tags:
        total = sum(rank_probs[tag])
        if total > 0:
            rank_probs[tag] = [
                round((p / total) * 100, 1) for p in rank_probs[tag]
            ]

    return rank_probs


class PredictionCog(commands.Cog, name="Prediction"):
    """Clan war outcome prediction module."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    @commands.command(name="prediction", aliases=["tahmin"])
    async def prediction_cmd(self, ctx: commands.Context, *args) -> None:
        """War outcome prediction. (!prediction or !prediction extra)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        extra_info = any(a.lower() in ("extra", "ekstra") for a in args)
        msg = await ctx.send(t("prediction.gathering"))

        race = await self.api.get_current_river_race()
        if not race or "clans" not in race:
            await msg.edit(content=t("prediction.no_active_race"))
            return

        clans_in_race = race["clans"]
        if not clans_in_race:
            await msg.edit(content=t("prediction.no_clan_data"))
            return

        tags = [c["tag"] for c in clans_in_race]
        names = {c["tag"]: c.get("name", "?") for c in clans_in_race}

        warlog_tasks = [self.api.get_river_race_log_for(tag) for tag in tags]
        warlogs = await asyncio.gather(*warlog_tasks)

        clan_stats: list[tuple[str, str, float, float]] = []
        detail_lines: list[str] = []
        for tag, warlog_data in zip(tags, warlogs):
            fame_history = _extract_fame_history(warlog_data, tag)

            mu, sigma = _compute_stats(fame_history)
            clan_name = names.get(tag, "?")
            clan_stats.append((tag, clan_name, mu, sigma))

            cv = (sigma / mu * 100) if mu > 0 else 0
            detail_lines.append(
                f"• **{clan_name}** – μ={mu:,.0f}  σ={sigma:,.0f}  "
                f"CV={cv:.0f}%  ({len(fame_history)}w)"
            )

        probabilities = _compute_rank_probabilities(clan_stats)

        embed = discord.Embed(
            title=t("prediction.embed_title"),
            description=t("prediction.embed_desc", weeks=MAX_WAR_HISTORY, lines="\n".join(detail_lines)),
            color=0x9B59B6,
        )

        rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

        our_tag_clean = clean_tag(CLAN_TAG)
        sorted_clans = sorted(
            clan_stats,
            key=lambda c: clean_tag(c[0]) != our_tag_clean,
        )

        for tag, name, mu, sigma in sorted_clans:
            probs = probabilities.get(tag, [0] * len(clan_stats))
            is_ours = clean_tag(tag) == our_tag_clean
            header = f"{'⭐ ' if is_ours else ''}{name}"

            lines = []
            for rank_idx, pct in enumerate(probs):
                bar_len = int(pct / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                lines.append(f"{rank_emojis[rank_idx]} {bar} **{pct}%**")

            embed.add_field(name=header, value="\n".join(lines), inline=False)

        our_probs = probabilities.get(CLAN_TAG, [])
        if our_probs:
            best_rank = our_probs.index(max(our_probs)) + 1
            embed.set_footer(
                text=t("prediction.best_rank", rank=best_rank, prob=max(our_probs))
            )

        await msg.delete()
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PredictionCog(bot))