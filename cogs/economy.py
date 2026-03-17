from __future__ import annotations

from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import themed_embed


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _ensure_profile(self, guild_id: int, user_id: int, data: dict) -> dict:
        g, u = str(guild_id), str(user_id)
        guild = data.setdefault(g, {})
        return guild.setdefault(u, {"xp": 0, "level": 1, "messages": 0, "coins": 0, "last_daily": "", "voice_seconds": 0})

    @app_commands.command(name="balance", description="Показать баланс")
    async def balance(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        target = user or interaction.user
        data = self.bot.users_db.read()
        profile = self._ensure_profile(interaction.guild.id, target.id, data)
        self.bot.users_db.write(data)
        embed = themed_embed("💰 Баланс", f"{target.mention}\n**{profile.get('coins', 0)}** монет")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Ежедневная награда")
    async def daily(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        reward = self.bot.settings.daily_reward
        result = {"ok": False, "coins": 0, "last": None}

        def updater(data: dict) -> None:
            profile = self._ensure_profile(interaction.guild.id, interaction.user.id, data)
            last_raw = str(profile.get("last_daily", ""))
            last = datetime.fromisoformat(last_raw) if last_raw else None
            if last and now - last < timedelta(hours=24):
                result["ok"] = False
                result["coins"] = int(profile.get("coins", 0))
                result["last"] = last
                return
            profile["coins"] = int(profile.get("coins", 0)) + reward
            profile["last_daily"] = now.isoformat()
            result["ok"] = True
            result["coins"] = int(profile["coins"])

        self.bot.users_db.mutate(updater)

        if not result["ok"]:
            next_time = result["last"] + timedelta(hours=24)
            embed = themed_embed("⏳ Daily уже получен", f"Следующий раз: <t:{int(next_time.timestamp())}:R>")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = themed_embed("✅ Ежедневная награда", f"Получено: **{reward}**\nБаланс: **{result['coins']}**", success=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="Передать монеты")
    @app_commands.describe(user="Кому", amount="Сколько")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return
        if amount <= 0 or user.id == interaction.user.id:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Некорректный перевод."), ephemeral=True)
            return

        result = {"ok": False, "sender": 0}

        def updater(data: dict) -> None:
            sender = self._ensure_profile(interaction.guild.id, interaction.user.id, data)
            target = self._ensure_profile(interaction.guild.id, user.id, data)
            sender_balance = int(sender.get("coins", 0))
            if sender_balance < amount:
                result["ok"] = False
                result["sender"] = sender_balance
                return
            sender["coins"] = sender_balance - amount
            target["coins"] = int(target.get("coins", 0)) + amount
            result["ok"] = True
            result["sender"] = int(sender["coins"])

        self.bot.users_db.mutate(updater)

        if not result["ok"]:
            await interaction.response.send_message(embed=themed_embed("Недостаточно монет", f"У тебя: **{result['sender']}**"), ephemeral=True)
            return

        embed = themed_embed("💸 Перевод выполнен", f"{interaction.user.mention} → {user.mention}\nСумма: **{amount}**")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="Магазин ролей")
    async def shop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        data = self.bot.economy_db.read()
        guild_shop = data.get(str(interaction.guild.id), {}).get("roles", [])
        if not guild_shop:
            await interaction.response.send_message(embed=themed_embed("🛒 Магазин", "Магазин пуст."), ephemeral=True)
            return

        lines = ["**Магазин ролей**"]
        for item in guild_shop:
            lines.append(f"`{item['name']}` — {item['price']} монет (ID роли: {item['role_id']})")
        embed = themed_embed("🛒 Магазин ролей", "\n".join(lines[1:]))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="Купить роль в магазине")
    @app_commands.describe(item_name="Название товара")
    async def buy(self, interaction: discord.Interaction, item_name: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Только на сервере.", ephemeral=True)
            return

        data = self.bot.economy_db.read()
        guild_shop = data.get(str(interaction.guild.id), {}).get("roles", [])
        item = next((x for x in guild_shop if x["name"].lower() == item_name.lower()), None)
        if item is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Товар не найден."), ephemeral=True)
            return

        role = interaction.guild.get_role(int(item["role_id"]))
        if role is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Роль из магазина не найдена на сервере."), ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(embed=themed_embed("Инфо", "У тебя уже есть эта роль."), ephemeral=True)
            return

        result = {"ok": False, "balance": 0}

        def updater(users: dict) -> None:
            profile = self._ensure_profile(interaction.guild.id, interaction.user.id, users)
            balance = int(profile.get("coins", 0))
            if balance < int(item["price"]):
                result["ok"] = False
                result["balance"] = balance
                return
            profile["coins"] = balance - int(item["price"])
            result["ok"] = True
            result["balance"] = int(profile["coins"])

        self.bot.users_db.mutate(updater)

        if not result["ok"]:
            await interaction.response.send_message(embed=themed_embed("Недостаточно монет", f"Баланс: **{result['balance']}**"), ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Покупка в магазине")
        except discord.Forbidden:
            await interaction.response.send_message(embed=themed_embed("Ошибка прав", "Нет прав выдать эту роль."), ephemeral=True)
            return

        embed = themed_embed("✅ Покупка успешна", f"Товар: **{item['name']}**\nНовый баланс: **{result['balance']}**", success=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = Economy(bot)
    await bot.add_cog(cog)
