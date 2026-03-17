from __future__ import annotations

import random
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from config import Settings
from database import JsonStore
from utils.helpers import themed_embed
from utils.xp_system import level_from_xp


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings, users_db: JsonStore, voice_db: JsonStore) -> None:
        self.bot = bot
        self.settings = settings
        self.users_db = users_db
        self.voice_db = voice_db
        self.active_voice: dict[str, datetime] = {}
        self.voice_tick.start()

    def _external_multiplier(self, member: discord.Member) -> tuple[float, list[str]]:
        """Внешние факторы для XP: выходные/ночной режим/активный онлайн."""
        now = datetime.now(timezone.utc)
        multiplier = 1.0
        reasons: list[str] = []

        # Выходные: небольшой буст
        if now.weekday() in (5, 6):
            multiplier += 0.20
            reasons.append("Weekend +20%")

        # Вечерний прайм-тайм (UTC)
        if 18 <= now.hour <= 23:
            multiplier += 0.10
            reasons.append("Prime-time +10%")

        # Буст за активность сервера (много людей онлайн в voice)
        in_voice = sum(1 for m in member.guild.members if m.voice and m.voice.channel)
        if in_voice >= 5:
            multiplier += 0.15
            reasons.append("Voice party +15%")

        return multiplier, reasons

    def cog_unload(self) -> None:
        self.voice_tick.cancel()

    def _user_profile(self, guild_id: int, user_id: int) -> dict:
        g, u = str(guild_id), str(user_id)
        data = self.users_db.read()
        guild = data.setdefault(g, {})
        profile = guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": ""})
        self.users_db.write(data)
        return profile

    async def _apply_xp(self, member: discord.Member, delta: int, source: str) -> None:
        multiplier, reasons = self._external_multiplier(member)
        final_delta = max(1, int(delta * multiplier))
        old_level = self._user_profile(member.guild.id, member.id).get("level", 1)

        def mutate(data: dict) -> None:
            g, u = str(member.guild.id), str(member.id)
            guild = data.setdefault(g, {})
            profile = guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": ""})
            profile["xp"] = int(profile.get("xp", 0)) + final_delta
            profile["level"] = level_from_xp(int(profile["xp"]), self.settings.level_curve)

        self.users_db.mutate(mutate)
        new_level = self._user_profile(member.guild.id, member.id).get("level", 1)

        if new_level > old_level:
            try:
                await member.send(
                    embed=themed_embed(
                        "🎉 Level Up!",
                        (
                            f"Сервер: **{member.guild.name}**\n"
                            f"Новый уровень: **{new_level}**\n"
                            f"Источник XP: **{source}**\n"
                            f"Начислено XP: **+{final_delta}**"
                            + (f"\nБонусы: {', '.join(reasons)}" if reasons else "")
                        ),
                        success=True,
                    )
                )
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        xp = random.randint(self.settings.message_xp_min, self.settings.message_xp_max)
        await self._apply_xp(message.author, xp, "сообщения")

        def mutate(data: dict) -> None:
            g, u = str(message.guild.id), str(message.author.id)
            guild = data.setdefault(g, {})
            profile = guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": ""})
            profile["messages"] = int(profile.get("messages", 0)) + 1

        self.users_db.mutate(mutate)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        key = f"{member.guild.id}:{member.id}"
        now = datetime.now(timezone.utc)
        if before.channel is None and after.channel is not None:
            self.active_voice[key] = now
        elif before.channel is not None and after.channel is None:
            start = self.active_voice.pop(key, None)
            if start:
                await self._commit_voice(member, int((now - start).total_seconds()))

    async def _commit_voice(self, member: discord.Member, seconds: int) -> None:
        if seconds <= 0:
            return
        xp_delta = int((seconds / 60) * self.settings.voice_xp_per_minute)
        if xp_delta > 0:
            await self._apply_xp(member, xp_delta, "голос")

        def mutate_users(data: dict) -> None:
            g, u = str(member.guild.id), str(member.id)
            guild = data.setdefault(g, {})
            profile = guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": ""})
            profile["voice_seconds"] = int(profile.get("voice_seconds", 0)) + seconds

        self.users_db.mutate(mutate_users)

        def mutate_voice(data: dict) -> None:
            g, u = str(member.guild.id), str(member.id)
            guild = data.setdefault(g, {})
            guild[u] = int(guild.get(u, 0)) + seconds

        self.voice_db.mutate(mutate_voice)

    @tasks.loop(minutes=1)
    async def voice_tick(self) -> None:
        now = datetime.now(timezone.utc)
        for key, start in list(self.active_voice.items()):
            guild_id, user_id = map(int, key.split(":"))
            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(user_id) if guild else None
            if not member:
                self.active_voice.pop(key, None)
                continue

            delta = int((now - start).total_seconds())
            if delta > 0:
                self.active_voice[key] = now
                await self._commit_voice(member, delta)

    @voice_tick.before_loop
    async def before_voice_tick(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot, bot.settings, bot.users_db, bot.voice_db))
