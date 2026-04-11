"""
Clan Records Cog – Tracks clan and player records.
Notifications are sent to the "records" channel.
"""
import json
import logging
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.cr_api import ClashRoyaleAPI
from utils.config import CHANNEL_ID
from utils.channels import get_notification_channel
import utils.i18n as i18n

log = logging.getLogger(__name__)

RECORDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "clan_records.json"
)

RECORD_CATEGORIES = [
    "clan_trophies",
    "clan_war_fame",
    "individual_donations",
    "individual_fame",
    "member_count",
    "activity_score",
    "total_donations",
]

DEFAULT_RECORD = {
    "value": 0,
    "holder": "None yet",
    "holder_tag": "",
    "date": "",
    "history": [],
}


def _load_records() -> dict:
    try:
        with open(RECORDS_PATH, encoding="utf-8") as f:
            data = json.load(f)
            for key in RECORD_CATEGORIES:
                if key not in data:
                    data[key] = dict(DEFAULT_RECORD)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {key: dict(DEFAULT_RECORD) for key in RECORD_CATEGORIES}


def _save_records(records: dict) -> None:
    os.makedirs(os.path.dirname(RECORDS_PATH), exist_ok=True)
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


class RecordsCog(commands.Cog, name="Records"):
    """Clan record tracking system."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api: ClashRoyaleAPI = bot.cr_api

    def cog_unload(self) -> None:
        self.record_check_task.cancel()

    def _update_record(
        self, records: dict, category: str,
        value: float, holder: str, holder_tag: str = ""
    ) -> bool:
        if category not in records:
            records[category] = dict(DEFAULT_RECORD)

        current = records[category]
        if value > current.get("value", 0):
            now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")

            if current.get("value", 0) > 0:
                history_entry = {
                    "value": current["value"],
                    "holder": current.get("holder", "?"),
                    "date": current.get("date", "?"),
                }
                if "history" not in current:
                    current["history"] = []
                current["history"].insert(0, history_entry)
                current["history"] = current["history"][:10]

            current["value"] = value
            current["holder"] = holder
            current["holder_tag"] = holder_tag
            current["date"] = now

            return True
        return False

    async def _check_records(self) -> list[tuple[str, str, float, str]]:
        records = _load_records()
        new_records: list[tuple[str, str, float, str]] = []

        clan = await self.api.get_clan_info()
        if not clan:
            return []

        members = await self.api.get_clan_members()
        if not members:
            return []

        clan_name = clan.get("name", "Clan")

        # 🏆 Clan Trophies
        clan_score = clan.get("clanScore", 0)
        if self._update_record(records, "clan_trophies", clan_score, clan_name):
            new_records.append(("clan_trophies", clan_name, clan_score, "trophies"))

        # 👥 Member Count
        member_count = clan.get("members", 0)
        if self._update_record(records, "member_count", member_count, clan_name):
            new_records.append(("member_count", clan_name, member_count, "members"))

        # 📤 Individual Donations
        for m in members:
            donations = m.get("donations", 0)
            name = m.get("name", "?")
            tag = m.get("tag", "")
            if self._update_record(records, "individual_donations", donations, name, tag):
                new_records.append(("individual_donations", name, donations, "cards"))

        # 🎁 Total Clan Donations
        total_donations = sum(m.get("donations", 0) for m in members)
        if self._update_record(records, "total_donations", total_donations, clan_name):
            new_records.append(("total_donations", clan_name, total_donations, "cards"))

        # ⚔️ War data
        race = await self.api.get_current_river_race()
        if race and "clan" in race:
            participants = race["clan"].get("participants", [])

            total_fame = sum(p.get("fame", 0) for p in participants)
            if self._update_record(records, "clan_war_fame", total_fame, clan_name):
                new_records.append(("clan_war_fame", clan_name, total_fame, "fame"))

            for p in participants:
                fame = p.get("fame", 0)
                name = p.get("name", "?")
                tag = p.get("tag", "")
                if self._update_record(records, "individual_fame", fame, name, tag):
                    new_records.append(("individual_fame", name, fame, "fame"))

        # 📊 Activity Score
        db = self.bot.db
        activity_scores = await db.get_activity_scores()
        if activity_scores:
            for entry in activity_scores:
                score = entry.get("score", 0)
                name = entry.get("player_name", "?")
                tag = entry.get("player_tag", "")
                if self._update_record(records, "activity_score", score, name, tag):
                    new_records.append(("activity_score", name, score, "score"))

        _save_records(records)
        return new_records

    # ── Commands ───────────────────────────────────────────────────────

    @commands.command(name="records", aliases=["rekorlar"])
    async def records_cmd(self, ctx: commands.Context) -> None:
        """Shows all clan records (!records or !rekorlar)"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        async with ctx.typing():
            await self._check_records()
            records = _load_records()

            embed = discord.Embed(
                title=t("records.title"),
                description=t("records.desc"),
                color=0xF1C40F,
            )

            for key in RECORD_CATEGORIES:
                record = records.get(key, DEFAULT_RECORD)
                value = record.get("value", 0)
                holder = record.get("holder", t("records.default_holder"))
                date = record.get("date", t("records.default_date"))
                
                cat_name = t(f"records.categories.{key}.name")
                unit = t(f"records.categories.{key}.unit")
                emoji = {"clan_trophies": "🏆", "clan_war_fame": "⚔️", "individual_donations": "📤", "individual_fame": "🏅", "member_count": "👥", "activity_score": "📊", "total_donations": "🎁"}.get(key, "🎖️")

                if value > 0:
                    if isinstance(value, float):
                        value_str = f"{value:.1f}"
                    else:
                        value_str = f"{value:,}"

                    embed.add_field(
                        name=f"{emoji} {cat_name}",
                        value=t("records.field_value", value=value_str, unit=unit, holder=holder, date=date),
                        inline=True,
                    )
                else:
                    embed.add_field(
                        name=f"{emoji} {cat_name}",
                        value=t("records.no_record"),
                        inline=True,
                    )

            embed.set_footer(
                text=t("records.footer")
            )

        await ctx.send(embed=embed)

    @commands.command(name="record_history", aliases=["rekor_gecmis", "rekor_geçmiş"])
    async def record_history_cmd(self, ctx: commands.Context, category: str = None) -> None:
        """Shows history of records broken (!record_history [category])"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        records = _load_records()

        category_map = {
            "trophies": "clan_trophies",
            "war": "clan_war_fame",
            "donation": "individual_donations",
            "donations": "individual_donations",
            "fame": "individual_fame",
            "members": "member_count",
            "activity": "activity_score",
            "total": "total_donations",
        }

        if category:
            key = category_map.get(category.lower())
            if not key:
                # remove duplicates from display
                valid_vals = set(category_map.values())
                valid_dict = {v: k for k, v in category_map.items()}
                valid_keys = ", ".join(f"`{k}`" for k in valid_dict.keys())
                await ctx.send(t("records.history.invalid_category", valid_keys=valid_keys))
                return
            categories_to_show = [key]
        else:
            categories_to_show = RECORD_CATEGORIES

        embed = discord.Embed(
            title=t("records.history.title"),
            color=0x9B59B6,
        )

        has_history = False

        for key in categories_to_show:
            record = records.get(key, DEFAULT_RECORD)
            history = record.get("history", [])

            if not history:
                continue

            has_history = True
            lines = []

            current_value = record.get("value", 0)
            current_holder = record.get("holder", "?")
            current_date = record.get("date", "?")
            
            cat_name = t(f"records.categories.{key}.name")
            unit = t(f"records.categories.{key}.unit")
            emoji = {"clan_trophies": "🏆", "clan_war_fame": "⚔️", "individual_donations": "📤", "individual_fame": "🏅", "member_count": "👥", "activity_score": "📊", "total_donations": "🎁"}.get(key, "🎖️")

            if isinstance(current_value, float):
                cv_str = f"{current_value:.1f}"
            else:
                cv_str = f"{current_value:,}"

            lines.append(
                t("records.history.current", value=cv_str, unit=unit, holder=current_holder, date=current_date)
            )

            for i, h in enumerate(history[:5], 2):
                h_value = h.get("value", 0)
                if isinstance(h_value, float):
                    hv_str = f"{h_value:.1f}"
                else:
                    hv_str = f"{h_value:,}"

                lines.append(
                    t("records.history.past", index=i, value=hv_str, unit=unit, holder=h.get("holder", "?"), date=h.get('date', '?'))
                )

            embed.add_field(
                name=f"{emoji} {cat_name}",
                value="\n".join(lines),
                inline=False,
            )

        if not has_history:
            embed.description = t("records.history.empty")

        await ctx.send(embed=embed)

    @commands.command(name="reset_record", aliases=["rekor_sifirla", "rekor_sıfırla"])
    @commands.has_permissions(administrator=True)
    async def reset_record_cmd(self, ctx: commands.Context, category: str = None) -> None:
        """Resets records – Admin only (!reset_record [category])"""
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        
        category_map = {
            "trophies": "clan_trophies",
            "war": "clan_war_fame",
            "donation": "individual_donations",
            "fame": "individual_fame",
            "members": "member_count",
            "activity": "activity_score",
            "total": "total_donations",
        }

        if category:
            key = category_map.get(category.lower())
            if not key:
                await ctx.send(t("records.history.invalid_category", valid_keys=", ".join(f"`{k}`" for k in set(category_map.values()))))
                return

            records = _load_records()
            records[key] = dict(DEFAULT_RECORD)
            _save_records(records)
            
            cat_name = t(f"records.categories.{key}.name")
            await ctx.send(t("records.reset.success", name=cat_name))
        else:
            await ctx.send(t("records.reset.confirm_all"))

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15.0)
                if msg.content.lower() in ("yes", "evet", "y", "e"):
                    records = {key: dict(DEFAULT_RECORD) for key in RECORD_CATEGORIES}
                    _save_records(records)
                    await ctx.send(t("records.reset.all_success"))
                else:
                    await ctx.send(t("records.reset.cancelled"))
            except Exception:
                await ctx.send(t("records.reset.timeout"))

    @reset_record_cmd.error
    async def reset_record_error(self, ctx: commands.Context, error: Exception) -> None:
        def t(key, **kw): return i18n.get(ctx.guild.id if ctx.guild else 0, key, **kw)
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(t("records.reset.no_perm"))

    # ── Auto Record Check → records channel ──────────────────────────

    @tasks.loop(hours=2)
    async def record_check_task(self) -> None:
        new_records = await self._check_records()

        if not new_records:
            return

        channel = await get_notification_channel(self.bot, "records", CHANNEL_ID)
        if channel is None:
            return
            
        guild_id = channel.guild.id if hasattr(channel, "guild") else 0
        def t(key, **kw): return i18n.get(guild_id, key, **kw)

        for category_key, holder, value, _ in new_records:
            cat_name = t(f"records.categories.{category_key}.name", default=category_key)
            unit = t(f"records.categories.{category_key}.unit")
            emoji = {"clan_trophies": "🏆", "clan_war_fame": "⚔️", "individual_donations": "📤", "individual_fame": "🏅", "member_count": "👥", "activity_score": "📊", "total_donations": "🎁"}.get(category_key, "🎖️")

            if isinstance(value, float):
                value_str = f"{value:.1f}"
            else:
                value_str = f"{value:,}"

            now_str = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')
            embed = discord.Embed(
                title=t("records.notification.title"),
                description=t("records.notification.desc", emoji=emoji, name=cat_name, value=value_str, unit=unit, holder=holder, date=now_str),
                color=0xFFD700,
            )
            embed.set_footer(text=t("records.notification.footer"))

            await channel.send(embed=embed)

        log.info("Record check: %d new records broke", len(new_records))

    @record_check_task.before_loop
    async def before_record_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    cog = RecordsCog(bot)
    await bot.add_cog(cog)
    cog.record_check_task.start()