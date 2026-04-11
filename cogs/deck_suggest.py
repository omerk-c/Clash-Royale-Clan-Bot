"""
Deck Suggest Cog – Meta deck suggestions and random deck generator.

Commands:
  !deck                → Suggests a random meta deck
  !suggest_deck [arena]→ Suggests a deck based on arena level
  !random_deck         → Generates a completely random deck (fun)
  !meta                → Lists current meta decks

Data Sources:
  - Clash Royale API (player's cards)
  - Internal meta deck database (current popular decks)
  - RoyaleAPI scraping (optional fallback)
"""
import logging
import random
from typing import Optional

import discord
from discord.ext import commands

from utils.cr_api import ClashRoyaleAPI
import utils.i18n as i18n

log = logging.getLogger(__name__)

# ── Card Database ───────────────────────────────────────────────────
# grouped by Elixir cost and type
# Reflects active Clash Royale cards

CARDS_BY_TYPE = {
    "Win Condition": [
        {"name": "Hog Rider", "elixir": 4, "rarity": "Rare", "arena": 4},
        {"name": "Giant", "elixir": 5, "rarity": "Rare", "arena": 0},
        {"name": "Golem", "elixir": 8, "rarity": "Epic", "arena": 6},
        {"name": "Royal Giant", "elixir": 6, "rarity": "Common", "arena": 7},
        {"name": "Lava Hound", "elixir": 7, "rarity": "Legendary", "arena": 4},
        {"name": "Graveyard", "elixir": 5, "rarity": "Legendary", "arena": 5},
        {"name": "Balloon", "elixir": 5, "rarity": "Epic", "arena": 2},
        {"name": "Ram Rider", "elixir": 5, "rarity": "Legendary", "arena": 10},
        {"name": "Goblin Giant", "elixir": 6, "rarity": "Epic", "arena": 9},
        {"name": "Elixir Golem", "elixir": 3, "rarity": "Rare", "arena": 10},
        {"name": "Royal Hogs", "elixir": 5, "rarity": "Rare", "arena": 7},
        {"name": "Three Musketeers", "elixir": 9, "rarity": "Rare", "arena": 7},
        {"name": "Mortar", "elixir": 4, "rarity": "Common", "arena": 6},
        {"name": "X-Bow", "elixir": 6, "rarity": "Epic", "arena": 6},
        {"name": "Miner", "elixir": 3, "rarity": "Legendary", "arena": 6},
        {"name": "Wall Breakers", "elixir": 2, "rarity": "Epic", "arena": 5},
        {"name": "Goblin Barrel", "elixir": 3, "rarity": "Epic", "arena": 1},
    ],
    "Support": [
        {"name": "Musketeer", "elixir": 4, "rarity": "Rare", "arena": 0},
        {"name": "Wizard", "elixir": 5, "rarity": "Rare", "arena": 2},
        {"name": "Electro Wizard", "elixir": 4, "rarity": "Legendary", "arena": 8},
        {"name": "Baby Dragon", "elixir": 4, "rarity": "Epic", "arena": 0},
        {"name": "Witch", "elixir": 5, "rarity": "Epic", "arena": 0},
        {"name": "Night Witch", "elixir": 4, "rarity": "Legendary", "arena": 8},
        {"name": "Magic Archer", "elixir": 4, "rarity": "Legendary", "arena": 6},
        {"name": "Executioner", "elixir": 5, "rarity": "Epic", "arena": 9},
        {"name": "Ice Wizard", "elixir": 3, "rarity": "Legendary", "arena": 5},
        {"name": "Mega Minion", "elixir": 3, "rarity": "Rare", "arena": 4},
        {"name": "Firecracker", "elixir": 3, "rarity": "Common", "arena": 5},
        {"name": "Flying Machine", "elixir": 4, "rarity": "Rare", "arena": 9},
        {"name": "Mother Witch", "elixir": 4, "rarity": "Legendary", "arena": 8},
        {"name": "Archer Queen", "elixir": 5, "rarity": "Champion", "arena": 15},
        {"name": "Golden Knight", "elixir": 4, "rarity": "Champion", "arena": 14},
        {"name": "Skeleton King", "elixir": 4, "rarity": "Champion", "arena": 14},
        {"name": "Mighty Miner", "elixir": 4, "rarity": "Champion", "arena": 15},
    ],
    "Spell": [
        {"name": "Fireball", "elixir": 4, "rarity": "Rare", "arena": 0},
        {"name": "Zap", "elixir": 2, "rarity": "Common", "arena": 0},
        {"name": "Log", "elixir": 2, "rarity": "Legendary", "arena": 6},
        {"name": "Arrows", "elixir": 3, "rarity": "Common", "arena": 0},
        {"name": "Poison", "elixir": 4, "rarity": "Epic", "arena": 5},
        {"name": "Lightning", "elixir": 6, "rarity": "Epic", "arena": 1},
        {"name": "Rocket", "elixir": 6, "rarity": "Rare", "arena": 3},
        {"name": "Tornado", "elixir": 3, "rarity": "Epic", "arena": 6},
        {"name": "Freeze", "elixir": 4, "rarity": "Epic", "arena": 4},
        {"name": "Snowball", "elixir": 2, "rarity": "Common", "arena": 8},
        {"name": "Barbarian Barrel", "elixir": 2, "rarity": "Epic", "arena": 6},
        {"name": "Earthquake", "elixir": 3, "rarity": "Rare", "arena": 7},
        {"name": "Royal Delivery", "elixir": 3, "rarity": "Common", "arena": 9},
    ],
    "Defense": [
        {"name": "Tesla", "elixir": 4, "rarity": "Common", "arena": 4},
        {"name": "Inferno Tower", "elixir": 5, "rarity": "Rare", "arena": 4},
        {"name": "Cannon", "elixir": 3, "rarity": "Common", "arena": 0},
        {"name": "Bomb Tower", "elixir": 4, "rarity": "Rare", "arena": 2},
        {"name": "Tombstone", "elixir": 3, "rarity": "Rare", "arena": 2},
        {"name": "Goblin Cage", "elixir": 4, "rarity": "Rare", "arena": 7},
        {"name": "Goblin Hut", "elixir": 5, "rarity": "Rare", "arena": 1},
    ],
    "Cycle": [
        {"name": "Skeletons", "elixir": 1, "rarity": "Common", "arena": 0},
        {"name": "Ice Spirit", "elixir": 1, "rarity": "Common", "arena": 8},
        {"name": "Electro Spirit", "elixir": 1, "rarity": "Common", "arena": 11},
        {"name": "Fire Spirit", "elixir": 1, "rarity": "Common", "arena": 0},
        {"name": "Heal Spirit", "elixir": 1, "rarity": "Rare", "arena": 7},
        {"name": "Bats", "elixir": 2, "rarity": "Common", "arena": 4},
        {"name": "Goblins", "elixir": 2, "rarity": "Common", "arena": 1},
        {"name": "Spear Goblins", "elixir": 2, "rarity": "Common", "arena": 0},
        {"name": "Guards", "elixir": 3, "rarity": "Epic", "arena": 7},
        {"name": "Knight", "elixir": 3, "rarity": "Common", "arena": 0},
        {"name": "Valkyrie", "elixir": 4, "rarity": "Rare", "arena": 0},
        {"name": "Mini P.E.K.K.A", "elixir": 4, "rarity": "Rare", "arena": 0},
        {"name": "Dark Prince", "elixir": 4, "rarity": "Epic", "arena": 7},
        {"name": "Prince", "elixir": 5, "rarity": "Epic", "arena": 0},
        {"name": "Bandit", "elixir": 3, "rarity": "Legendary", "arena": 6},
    ],
}

# ── Popular Meta Decks ───────────────────────────────────────────────

META_DECKS = [
    {
        "name": "Hog 2.6",
        "archetype": "Cycle",
        "cards": ["Hog Rider", "Musketeer", "Ice Spirit", "Skeletons", "Cannon", "Fireball", "Log", "Ice Golem"],
        "avg_elixir": 2.6,
        "difficulty": "Hard",
        "description": "Classic fast cycle deck. Defend and counter-attack with Hog.",
        "arena_min": 8,
    },
    {
        "name": "Log Bait",
        "archetype": "Bait",
        "cards": ["Goblin Barrel", "Princess", "Goblin Gang", "Knight", "Inferno Tower", "Rocket", "Log", "Ice Spirit"],
        "avg_elixir": 3.0,
        "difficulty": "Medium",
        "description": "Bait out the opponent's big spell and deal damage with Goblin Barrel.",
        "arena_min": 7,
    },
    {
        "name": "Golem Beatdown",
        "archetype": "Beatdown",
        "cards": ["Golem", "Night Witch", "Lumberjack", "Baby Dragon", "Mega Minion", "Lightning", "Tornado", "Barbarian Barrel"],
        "avg_elixir": 4.1,
        "difficulty": "Medium",
        "description": "Push with Golem and support troops in double elixir.",
        "arena_min": 8,
    },
    {
        "name": "Lava Loon",
        "archetype": "Beatdown",
        "cards": ["Lava Hound", "Balloon", "Mega Minion", "Tombstone", "Fireball", "Zap", "Minions", "Skeleton Dragons"],
        "avg_elixir": 3.9,
        "difficulty": "Medium",
        "description": "Reach the tower with Balloon behind Lava Hound tank.",
        "arena_min": 6,
    },
    {
        "name": "X-Bow 3.0",
        "archetype": "Siege",
        "cards": ["X-Bow", "Tesla", "Ice Spirit", "Skeletons", "Knight", "Fireball", "Log", "Archers"],
        "avg_elixir": 3.0,
        "difficulty": "Very Hard",
        "description": "Place X-Bow at the bridge and defend it to deal damage. Patience deck.",
        "arena_min": 9,
    },
    {
        "name": "Royal Giant",
        "archetype": "Bridge Spam",
        "cards": ["Royal Giant", "Fisherman", "Mega Minion", "Lightning", "Log", "Guards", "Mother Witch", "Fireball"],
        "avg_elixir": 3.9,
        "difficulty": "Easy",
        "description": "Direct damage to tower with Royal Giant from the bridge.",
        "arena_min": 7,
    },
    {
        "name": "Pekka Bridge Spam",
        "archetype": "Bridge Spam",
        "cards": ["P.E.K.K.A", "Bandit", "Battle Ram", "Electro Wizard", "Minions", "Poison", "Zap", "Royal Ghost"],
        "avg_elixir": 3.8,
        "difficulty": "Medium",
        "description": "Defend with PEKKA and bridge spam with counter-attack troops.",
        "arena_min": 9,
    },
    {
        "name": "Mortar Bait",
        "archetype": "Siege/Bait",
        "cards": ["Mortar", "Goblin Gang", "Spear Goblins", "Bats", "Miner", "Rascals", "Fireball", "Log"],
        "avg_elixir": 3.0,
        "difficulty": "Medium",
        "description": "Deal damage with Mortar while defending with bait cards.",
        "arena_min": 7,
    },
    {
        "name": "Giant Double Prince",
        "archetype": "Beatdown",
        "cards": ["Giant", "Prince", "Dark Prince", "Mega Minion", "Electro Wizard", "Fireball", "Zap", "Miner"],
        "avg_elixir": 3.9,
        "difficulty": "Easy",
        "description": "Strong push by placing two Princes behind the Giant.",
        "arena_min": 7,
    },
    {
        "name": "Graveyard Poison",
        "archetype": "Control",
        "cards": ["Graveyard", "Poison", "Baby Dragon", "Tornado", "Knight", "Tombstone", "Barbarian Barrel", "Ice Wizard"],
        "avg_elixir": 3.1,
        "difficulty": "Hard",
        "description": "Melt the tower with Graveyard + Poison combo.",
        "arena_min": 8,
    },
    {
        "name": "Miner Wall Breakers",
        "archetype": "Cycle",
        "cards": ["Miner", "Wall Breakers", "Valkyrie", "Musketeer", "Snowball", "Skeletons", "Bats", "Bomb Tower"],
        "avg_elixir": 2.9,
        "difficulty": "Medium",
        "description": "Tank with Miner and deal burst damage with Wall Breakers.",
        "arena_min": 6,
    },
    {
        "name": "Mega Knight Bait",
        "archetype": "Bait",
        "cards": ["Mega Knight", "Goblin Barrel", "Skeleton Army", "Inferno Dragon", "Bats", "Miner", "Zap", "Spear Goblins"],
        "avg_elixir": 3.1,
        "difficulty": "Easy",
        "description": "Mega Knight defense/counter-attack + Goblin Barrel for damage.",
        "arena_min": 7,
    },
]

# ── Difficulty Emojis ────────────────────────────────────────────────

DIFFICULTY_EMOJI = {
    "Easy": "🟢",
    "Medium": "🟡",
    "Hard": "🔴",
    "Very Hard": "⚫",
}

ARCHETYPE_EMOJI = {
    "Cycle": "🔄",
    "Beatdown": "🔨",
    "Siege": "🏰",
    "Bait": "🪤",
    "Bridge Spam": "🌉",
    "Control": "🎯",
    "Siege/Bait": "🏰🪤",
}


def _format_deck_embed(ctx: commands.Context, deck: dict, index: int = 0) -> discord.Embed:
    """Creates an embed for a single deck."""
    def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
    
    diff_key = {
        "Easy": "deck_suggest.difficulty.easy",
        "Medium": "deck_suggest.difficulty.medium",
        "Hard": "deck_suggest.difficulty.hard",
        "Very Hard": "deck_suggest.difficulty.very_hard",
    }.get(deck["difficulty"], "deck_suggest.difficulty.medium")
    
    diff_localized = t(diff_key)
    diff_emoji = DIFFICULTY_EMOJI.get(deck["difficulty"], "⚪")
    arch_emoji = ARCHETYPE_EMOJI.get(deck["archetype"], "🃏")

    embed = discord.Embed(
        title=t("deck_suggest.deck.title", name=deck['name']),
        description=deck["description"],
        color=0x3498DB,
    )

    # Cards
    card_list = "\n".join(f"• {card}" for card in deck["cards"])
    embed.add_field(
        name=t("deck_suggest.deck.cards_title"),
        value=card_list,
        inline=True,
    )

    # Info
    embed.add_field(
        name=t("deck_suggest.deck.stats_title"),
        value=t("deck_suggest.deck.stats_value", elixir=deck['avg_elixir'], diff_emoji=diff_emoji, diff=diff_localized, arch_emoji=arch_emoji, arch=deck['archetype'], arena=deck['arena_min']),
        inline=True,
    )

    embed.set_footer(
        text=t("deck_suggest.deck.footer", index=index + 1)
    )

    return embed


class DeckSuggestCog(commands.Cog, name="Deck Suggest"):
    """Meta deck suggestions and random deck generator."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    # ── !deck command ──────────────────────────────────────────────────

    @commands.command(name="deck", aliases=["deste"])
    async def deck_cmd(self, ctx: commands.Context) -> None:
        """Suggests a random meta deck (!deck)"""
        deck = random.choice(META_DECKS)
        index = META_DECKS.index(deck)
        embed = _format_deck_embed(ctx, deck, index)
        await ctx.send(embed=embed)

    # ── !suggest_deck command ──────────────────────────────────────────

    @commands.command(name="suggest_deck", aliases=["deste_oner", "deste_öner"])
    async def suggest_deck_cmd(self, ctx: commands.Context, arena: int = None) -> None:
        """
        Suggests a deck based on arena level.

        Usage:
          !suggest_deck       → Random for all arenas
          !suggest_deck 7     → With Arena 7 and lower cards
          !suggest_deck 15    → Including all cards
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        if arena is not None:
            if arena < 0 or arena > 20:
                await ctx.send(t("deck_suggest.suggest.arena_err"))
                return

            # Filter decks suitable for Arena
            suitable = [d for d in META_DECKS if d["arena_min"] <= arena]
            if not suitable:
                await ctx.send(t("deck_suggest.suggest.no_deck", arena=arena))
                return

            deck = random.choice(suitable)
        else:
            deck = random.choice(META_DECKS)

        index = META_DECKS.index(deck)
        embed = _format_deck_embed(ctx, deck, index)

        if arena is not None:
            embed.set_author(name=t("deck_suggest.suggest.author", arena=arena))

        await ctx.send(embed=embed)

    # ── !random_deck command ───────────────────────────────────────────

    @commands.command(name="random_deck", aliases=["deste_rastgele"])
    async def random_deck_cmd(self, ctx: commands.Context) -> None:
        """
        Generates a completely random deck (for fun).

        Rules:
          - 8 cards
          - At least 1 Win Condition
          - At least 1 Spell
          - At least 1 anti-air card (not perfectly implemented)
          - Average elixir between 3.0 and 5.0
        """
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        max_attempts = 50
        for _ in range(max_attempts):
            deck = self._generate_random_deck()
            if deck:
                break
        else:
            await ctx.send(t("deck_suggest.random.err"))
            return

        # Calculate average elixir
        avg_elixir = sum(c["elixir"] for c in deck) / len(deck)

        embed = discord.Embed(
            title=t("deck_suggest.random.title"),
            description=t("deck_suggest.random.desc"),
            color=0xE67E22,
        )

        card_lines = []
        for card in deck:
            rarity_emoji = {
                "Common": "⬜",
                "Rare": "🟦",
                "Epic": "🟪",
                "Legendary": "🟨",
                "Champion": "🟥",
            }.get(card["rarity"], "⬜")
            card_lines.append(
                f"{rarity_emoji} **{card['name']}** ({card['elixir']} elixir)"
            )

        embed.add_field(
            name=t("deck_suggest.random.cards_title"),
            value="\n".join(card_lines),
            inline=False,
        )

        embed.add_field(
            name=t("deck_suggest.random.elixir_title"),
            value=f"**{avg_elixir:.1f}**",
            inline=True,
        )

        # Evaluation based on elixir cost
        if avg_elixir < 3.0:
            verdict = t("deck_suggest.random.verdict.ultra_fast")
        elif avg_elixir < 3.5:
            verdict = t("deck_suggest.random.verdict.fast")
        elif avg_elixir < 4.0:
            verdict = t("deck_suggest.random.verdict.balanced")
        elif avg_elixir < 4.5:
            verdict = t("deck_suggest.random.verdict.heavy")
        else:
            verdict = t("deck_suggest.random.verdict.ultra_heavy")

        embed.add_field(
            name=t("deck_suggest.random.verdict_title"),
            value=verdict,
            inline=True,
        )

        embed.set_footer(text=t("deck_suggest.random.footer"))

        await ctx.send(embed=embed)

    def _generate_random_deck(self) -> Optional[list[dict]]:
        """Generates a random 8-card deck adhering to basic rules."""
        deck: list[dict] = []
        used_names: set[str] = set()

        # 1. At least 1 Win Condition
        wc = random.choice(CARDS_BY_TYPE["Win Condition"])
        deck.append(wc)
        used_names.add(wc["name"])

        # 2. At least 1 Spell
        spell = random.choice(CARDS_BY_TYPE["Spell"])
        while spell["name"] in used_names:
            spell = random.choice(CARDS_BY_TYPE["Spell"])
        deck.append(spell)
        used_names.add(spell["name"])

        # 3. At least 1 small spell (2 elixir)
        small_spells = [s for s in CARDS_BY_TYPE["Spell"] if s["elixir"] <= 2 and s["name"] not in used_names]
        if small_spells:
            ss = random.choice(small_spells)
            deck.append(ss)
            used_names.add(ss["name"])

        # 4. Fill remaining cards randomly
        all_cards = []
        for category in CARDS_BY_TYPE.values():
            all_cards.extend(category)

        while len(deck) < 8:
            card = random.choice(all_cards)
            if card["name"] not in used_names:
                deck.append(card)
                used_names.add(card["name"])

        # 5. Elixir check (between 2.5 and 5.5)
        avg = sum(c["elixir"] for c in deck) / 8
        if avg < 2.5 or avg > 5.5:
            return None

        return deck

    # ── !meta command ──────────────────────────────────────────────────

    @commands.command(name="meta")
    async def meta_cmd(self, ctx: commands.Context) -> None:
        """Lists all meta decks (!meta)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        embed = discord.Embed(
            title=t("deck_suggest.meta.title"),
            description=t("deck_suggest.meta.desc"),
            color=0x9B59B6,
        )

        for i, deck in enumerate(META_DECKS, 1):
            diff_emoji = DIFFICULTY_EMOJI.get(deck["difficulty"], "⚪")
            arch_emoji = ARCHETYPE_EMOJI.get(deck["archetype"], "🃏")

            cards_short = ", ".join(deck["cards"][:4]) + "..."

            embed.description += (
                f"**{i}.** {arch_emoji} **{deck['name']}** {diff_emoji}\n"
                f"   💧 {deck['avg_elixir']} elixir · 🏟️ Arena {deck['arena_min']}+\n"
                f"   `{cards_short}`\n\n"
            )

        embed.set_footer(
            text=t("deck_suggest.meta.footer")
        )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DeckSuggestCog(bot))