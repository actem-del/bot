from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import themed_embed
from utils.image_generator import render_profile_card


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _get_profile(self, guild_id: int, user_id: int) -> dict:
        data = self.bot.users_db.read()
        return data.get(str(guild_id), {}).get(
            str(user_id),
            {"xp": 0, "level": 1, "messages": 0, "coins": 0, "voice_seconds": 0},
        )

    @app_commands.command(name="profile", description="Показать карточку профиля")
    @app_commands.describe(user="Пользователь")
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        member = user or interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(member.id)
        if member is None:
            await interaction.response.send_message("Пользователь не найден.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        profile = self._get_profile(interaction.guild.id, member.id)
        image = await render_profile_card(member, profile)
        embed = themed_embed(
            title="🟥 Профиль участника",
            description=f"Карточка пользователя {member.mention}",
            success=True,
        )
        embed.set_image(url="attachment://profile.png")
        await interaction.followup.send(embed=embed, file=discord.File(image, filename="profile.png"))


async def setup(bot: commands.Bot) -> None:
    cog = Profile(bot)
    await bot.add_cog(cog)
