from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.helpers import themed_embed
from utils.image_generator import render_love_profile_card


class LavRooms(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _guild_data(self, guild_id: int, data: dict) -> dict:
        return data.setdefault(
            str(guild_id),
            {
                "hub_channel_id": 0,
                "category_id": 0,
                "pairs": {},
                "marriages": {},
                "pending": {},
            },
        )

    @staticmethod
    def _pair_key(user_a: int, user_b: int) -> str:
        x, y = sorted((user_a, user_b))
        return f"{x}:{y}"

    def _spouse_id(self, guild_id: int, user_id: int) -> int | None:
        data = self.bot.lavrooms_db.read().get(str(guild_id), {})
        spouse = data.get("marriages", {}).get(str(user_id))
        return int(spouse) if spouse is not None else None

    def _room_for_pair(self, guild_id: int, user_a: int, user_b: int) -> int | None:
        data = self.bot.lavrooms_db.read().get(str(guild_id), {})
        room_id = data.get("pairs", {}).get(self._pair_key(user_a, user_b))
        return int(room_id) if room_id else None

    @staticmethod
    def _is_admin(interaction: discord.Interaction) -> bool:
        return bool(interaction.user.guild_permissions.administrator)

    @app_commands.command(name="loveroom_setup", description="[ADMIN] Настроить хаб для love room")
    async def loveroom_setup(
        self,
        interaction: discord.Interaction,
        hub_channel: discord.VoiceChannel,
        category: discord.CategoryChannel | None = None,
    ) -> None:
        if interaction.guild is None or not self._is_admin(interaction):
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Нужны права администратора."), ephemeral=True)
            return

        target_category = category or hub_channel.category
        if target_category is None:
            await interaction.response.send_message(
                embed=themed_embed("Ошибка", "Укажи категорию или помести хаб в категорию."),
                ephemeral=True,
            )
            return

        def updater(data: dict) -> None:
            guild_data = self._guild_data(interaction.guild.id, data)
            guild_data["hub_channel_id"] = hub_channel.id
            guild_data["category_id"] = target_category.id

        self.bot.lavrooms_db.mutate(updater)
        await interaction.response.send_message(
            embed=themed_embed(
                "❤️ LoveRoom настроен",
                f"Хаб: {hub_channel.mention}\nКатегория: **{target_category.name}**",
                success=True,
            )
        )

    @app_commands.command(name="marry", description="Сделать предложение пользователю")
    async def marry(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Только на сервере."), ephemeral=True)
            return

        author = interaction.user
        if not isinstance(author, discord.Member):
            author = interaction.guild.get_member(author.id)
        if author is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Автор не найден."), ephemeral=True)
            return

        if user.bot or user.id == author.id:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Некорректный выбор партнера."), ephemeral=True)
            return

        if self._spouse_id(interaction.guild.id, author.id) is not None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Ты уже в браке."), ephemeral=True)
            return

        if self._spouse_id(interaction.guild.id, user.id) is not None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Этот пользователь уже в браке."), ephemeral=True)
            return

        def updater(data: dict) -> None:
            g = self._guild_data(interaction.guild.id, data)
            g.setdefault("pending", {})[str(user.id)] = author.id

        self.bot.lavrooms_db.mutate(updater)
        await interaction.response.send_message(
            embed=themed_embed(
                "💍 Предложение отправлено",
                f"{author.mention} сделал предложение {user.mention}.\n"
                f"Принятие: `/marry_accept user:@{author.display_name}`",
                success=True,
            )
        )

    @app_commands.command(name="marry_accept", description="Принять предложение о браке")
    async def marry_accept(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Только на сервере."), ephemeral=True)
            return

        if self._spouse_id(interaction.guild.id, interaction.user.id) is not None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Ты уже в браке."), ephemeral=True)
            return

        result = {"ok": False}

        def updater(data: dict) -> None:
            g = self._guild_data(interaction.guild.id, data)
            pending = g.setdefault("pending", {})
            marriages = g.setdefault("marriages", {})

            requester_id = pending.get(str(interaction.user.id))
            if requester_id is None or int(requester_id) != user.id:
                return

            if marriages.get(str(interaction.user.id)) or marriages.get(str(user.id)):
                return

            marriages[str(interaction.user.id)] = user.id
            marriages[str(user.id)] = interaction.user.id
            pending.pop(str(interaction.user.id), None)
            result["ok"] = True

        self.bot.lavrooms_db.mutate(updater)
        if not result["ok"]:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Не найдено подходящее предложение."), ephemeral=True)
            return

        await interaction.response.send_message(
            embed=themed_embed(
                "💞 Брак заключен",
                f"{interaction.user.mention} и {user.mention} теперь в браке!",
                success=True,
            )
        )

    @app_commands.command(name="divorce", description="Развестись")
    async def divorce(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Только на сервере."), ephemeral=True)
            return

        spouse_id = self._spouse_id(interaction.guild.id, interaction.user.id)
        if spouse_id is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Ты не состоишь в браке."), ephemeral=True)
            return

        def updater(data: dict) -> None:
            g = self._guild_data(interaction.guild.id, data)
            marriages = g.setdefault("marriages", {})
            pairs = g.setdefault("pairs", {})
            marriages.pop(str(interaction.user.id), None)
            marriages.pop(str(spouse_id), None)
            pairs.pop(self._pair_key(interaction.user.id, spouse_id), None)

        self.bot.lavrooms_db.mutate(updater)
        await interaction.response.send_message(embed=themed_embed("💔 Развод", "Брак расторгнут."), ephemeral=True)

    @app_commands.command(name="loveroom", description="Управление love room")
    async def loveroom(self, interaction: discord.Interaction, action: str, name: str | None = None) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Только на сервере."), ephemeral=True)
            return

        spouse_id = self._spouse_id(interaction.guild.id, interaction.user.id)
        if spouse_id is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Сначала заключи брак через /marry."), ephemeral=True)
            return

        room_id = self._room_for_pair(interaction.guild.id, interaction.user.id, spouse_id)
        channel = interaction.guild.get_channel(room_id) if room_id else None
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Ваша love room не активна. Зайдите в хаб-канал."), ephemeral=True)
            return

        act = action.lower().strip()
        if act == "rename":
            if not name:
                await interaction.response.send_message(embed=themed_embed("Ошибка", "Для rename укажи name."), ephemeral=True)
                return
            await channel.edit(name=name[:90])
            await interaction.response.send_message(embed=themed_embed("✅ LoveRoom", f"Новое имя: **{name[:90]}**", success=True), ephemeral=True)
            return

        if act in {"lock", "unlock"}:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = act != "lock"
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            state = "закрыта" if act == "lock" else "открыта"
            await interaction.response.send_message(embed=themed_embed("✅ LoveRoom", f"Комната теперь **{state}**", success=True), ephemeral=True)
            return

        await interaction.response.send_message(embed=themed_embed("Ошибка", "action: rename / lock / unlock"), ephemeral=True)

    @app_commands.command(name="loveprofile", description="Показать любовный профиль пары")
    async def loveprofile(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Только на сервере."), ephemeral=True)
            return

        spouse_id = self._spouse_id(interaction.guild.id, interaction.user.id)
        if spouse_id is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Сначала заключи брак через /marry."), ephemeral=True)
            return

        spouse = interaction.guild.get_member(spouse_id)
        if spouse is None:
            await interaction.response.send_message(embed=themed_embed("Ошибка", "Партнер не найден."), ephemeral=True)
            return

        users_data = self.bot.users_db.read().get(str(interaction.guild.id), {})
        p1 = users_data.get(str(interaction.user.id), {})
        p2 = users_data.get(str(spouse.id), {})

        await interaction.response.defer(thinking=True)
        image = await render_love_profile_card(interaction.user, spouse, p1, p2)
        embed = themed_embed("❤️ Love Profile", f"Пара: {interaction.user.mention} & {spouse.mention}", success=True)
        embed.set_image(url="attachment://loveprofile.png")
        await interaction.followup.send(embed=embed, file=discord.File(image, filename="loveprofile.png"))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if member.bot:
            return

        if after.channel is not None:
            await self._maybe_create_or_join_love_room(member, after.channel)
        if before.channel is not None:
            await self._maybe_cleanup_room(member.guild, before.channel)

    async def _maybe_create_or_join_love_room(self, member: discord.Member, joined_channel: discord.VoiceChannel) -> None:
        data = self.bot.lavrooms_db.read().get(str(member.guild.id), {})
        hub_id = int(data.get("hub_channel_id", 0))
        category_id = int(data.get("category_id", 0))

        if hub_id <= 0 or joined_channel.id != hub_id:
            return

        spouse_id = self._spouse_id(member.guild.id, member.id)
        if spouse_id is None:
            return

        spouse = member.guild.get_member(spouse_id)
        if spouse is None:
            return

        pair_key = self._pair_key(member.id, spouse.id)
        room_id = data.get("pairs", {}).get(pair_key)
        existing = member.guild.get_channel(int(room_id)) if room_id else None
        if isinstance(existing, discord.VoiceChannel):
            await member.move_to(existing)
            return

        category = member.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            return

        room_name = f"❤️ {member.display_name} + {spouse.display_name}"
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            member: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True),
            spouse: discord.PermissionOverwrite(connect=True, view_channel=True, manage_channels=True),
        }

        new_room = await member.guild.create_voice_channel(
            name=room_name[:100],
            category=category,
            user_limit=2,
            overwrites=overwrites,
            reason="Auto love room creation",
        )

        await member.move_to(new_room)

        def updater(mut: dict) -> None:
            g = self._guild_data(member.guild.id, mut)
            g.setdefault("pairs", {})[pair_key] = new_room.id

        self.bot.lavrooms_db.mutate(updater)

    async def _maybe_cleanup_room(self, guild: discord.Guild, left_channel: discord.VoiceChannel) -> None:
        data = self.bot.lavrooms_db.read().get(str(guild.id), {})
        pairs = data.get("pairs", {})
        if str(left_channel.id) not in {str(v) for v in pairs.values()}:
            return
        if left_channel.members:
            return

        pair_key_to_delete: str | None = None
        for key, value in pairs.items():
            if int(value) == left_channel.id:
                pair_key_to_delete = key
                break

        try:
            await left_channel.delete(reason="Love room is empty")
        except discord.HTTPException:
            return

        if pair_key_to_delete is None:
            return

        def updater(mut: dict) -> None:
            g = self._guild_data(guild.id, mut)
            g.setdefault("pairs", {}).pop(pair_key_to_delete, None)

        self.bot.lavrooms_db.mutate(updater)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LavRooms(bot))
