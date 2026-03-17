from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import themed_embed


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _is_admin(interaction: discord.Interaction) -> bool:
        return bool(interaction.user.guild_permissions.administrator)

    def _ensure_profile(self, guild_id: int, user_id: int, data: dict) -> dict:
        g, u = str(guild_id), str(user_id)
        guild = data.setdefault(g, {})
        return guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": "", "voice_seconds": 0})

    @app_commands.command(name="admin_set_xp", description="[ADMIN] Установить XP")
    async def admin_set_xp(self, interaction: discord.Interaction, user: discord.Member, xp: int) -> None:
        if interaction.guild is None or not self._is_admin(interaction):
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Нужны права администратора."), ephemeral=True)
            return

        def updater(data: dict) -> None:
            profile = self._ensure_profile(interaction.guild.id, user.id, data)
            profile["xp"] = max(0, xp)

        self.bot.users_db.mutate(updater)
        await interaction.response.send_message(
            embed=themed_embed("🛠 XP обновлен", f"{user.mention}: **{max(0, xp)}**", success=True)
        )

    @app_commands.command(name="admin_add_coins", description="[ADMIN] Выдать монеты")
    async def admin_add_coins(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if interaction.guild is None or not self._is_admin(interaction):
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Нужны права администратора."), ephemeral=True)
            return

        def updater(data: dict) -> None:
            profile = self._ensure_profile(interaction.guild.id, user.id, data)
            profile["coins"] = int(profile.get("coins", 0)) + amount

        self.bot.users_db.mutate(updater)
        await interaction.response.send_message(
            embed=themed_embed("🛠 Монеты выданы", f"{user.mention}: **{amount}** монет", success=True)
        )

    @app_commands.command(name="admin_add_shop_role", description="[ADMIN] Добавить роль в магазин")
    async def admin_add_shop_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        price: int,
        item_name: str | None = None,
    ) -> None:
        if interaction.guild is None or not self._is_admin(interaction):
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Нужны права администратора."), ephemeral=True)
            return

        if price <= 0:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Цена должна быть больше 0."), ephemeral=True)
            return

        item = {
            "name": (item_name or role.name).strip(),
            "role_id": role.id,
            "price": price,
        }

        def updater(data: dict) -> None:
            g = str(interaction.guild.id)
            guild_shop = data.setdefault(g, {"roles": []})
            roles = guild_shop.setdefault("roles", [])
            roles[:] = [r for r in roles if int(r["role_id"]) != role.id]
            roles.append(item)

        self.bot.economy_db.mutate(updater)
        await interaction.response.send_message(
            embed=themed_embed("✅ Роль добавлена в магазин", f"**{item['name']}** — {price} монет", success=True)
        )


async def setup(bot: commands.Bot) -> None:
    cog = Admin(bot)
    await bot.add_cog(cog)
