import os

print("TOKEN_RAW:", repr(os.environ.get("DISCORD_TOKEN")))
print("ALL_ENV_HAS_TOKEN:", "DISCORD_TOKEN" in os.environ)
import discord
from discord.ext import commands

from config import get_settings
from database import JsonStore

COGS = [
    "cogs.leveling",
    "cogs.profile",
    "cogs.economy",
    "cogs.leaderboard",
    "cogs.admin",
    "cogs.lavrooms",
]


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        settings = get_settings()
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        intents.guilds = True

        super().__init__(command_prefix=settings.prefix, intents=intents)
        self.settings = settings
        self.users_db = JsonStore("data/users.json", default={})
        self.economy_db = JsonStore("data/economy.json", default={})
        self.voice_db = JsonStore("data/voice_time.json", default={})
        self.lavrooms_db = JsonStore("data/lavrooms.json", default={})
        self._did_guild_cleanup = False

    async def setup_hook(self) -> None:
        for ext in COGS:
            await self.load_extension(ext)

        global_commands = await self.tree.sync()
        print(f"Global sync complete: {len(global_commands)} commands")

    async def cleanup_guild_overrides(self) -> None:
        """Удаляем старые guild-overrides, чтобы не было дублей с глобальными командами."""
        if self._did_guild_cleanup:
            return

        for guild in self.guilds:
            self.tree.clear_commands(guild=discord.Object(id=guild.id))
            await self.tree.sync(guild=discord.Object(id=guild.id))
            print(f"Guild overrides cleared for {guild.name} ({guild.id})")

        extra_guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if extra_guild_id.isdigit():
            gid = int(extra_guild_id)
            self.tree.clear_commands(guild=discord.Object(id=gid))
            await self.tree.sync(guild=discord.Object(id=gid))
            print(f"Explicit guild overrides cleared for {gid}")

        self._did_guild_cleanup = True


bot = DiscordBot()


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (id={bot.user.id if bot.user else 'unknown'})")
    await bot.cleanup_guild_overrides()


@bot.command(name="sync")
@commands.has_guild_permissions(administrator=True)
async def sync_commands(ctx: commands.Context) -> None:
    """Ручная очистка guild-overrides + sync global (чтобы убрать дубли)."""
    if ctx.guild is None:
        await ctx.reply("Команда доступна только на сервере.")
        return

    gid = discord.Object(id=ctx.guild.id)
    bot.tree.clear_commands(guild=gid)
    await bot.tree.sync(guild=gid)
    global_synced = await bot.tree.sync()
    await ctx.reply(f"Готово. Глобальных команд: {len(global_synced)}. Дубли удалены.")


if __name__ == "__main__":
    bot.run(bot.settings.token)
