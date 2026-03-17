from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import themed_embed


class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Топ участников по XP/монетам")
    @app_commands.describe(metric="xp или coins")
    async def leaderboard(self, interaction: discord.Interaction, metric: str = "xp") -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        metric = metric.lower().strip()
        if metric not in {"xp", "coins", "messages", "voice_seconds"}:
            await interaction.response.send_message(
                embed=themed_embed("Ошибка", "Метрика: xp / coins / messages / voice_seconds"),
                ephemeral=True,
            )
            return

        guild_data = self.bot.users_db.read().get(str(interaction.guild.id), {})
        rows = sorted(guild_data.items(), key=lambda kv: int(kv[1].get(metric, 0)), reverse=True)[:10]
        if not rows:
            await interaction.response.send_message(embed=themed_embed("Лидерборд", "Пока нет данных."), ephemeral=True)
            return

        lines = [f"🏆 **Лидерборд по {metric.upper()}**"]
        for idx, (user_id, profile) in enumerate(rows, start=1):
            member = interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"User {user_id}"
            lines.append(f"`#{idx}` {name} — **{int(profile.get(metric, 0))}**")

        embed = themed_embed(f"🏆 Лидерборд по {metric.upper()}", "\n".join(lines[1:]))
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = Leaderboard(bot)
    await bot.add_cog(cog)
