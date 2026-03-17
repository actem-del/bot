from __future__ import annotations

from datetime import datetime, timezone

import discord

THEME_RED = 0xD7263D
THEME_DARK_RED = 0x6E121C


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "Неизвестно"
    return value.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")


def fmt_hours(seconds: int) -> str:
    return f"{seconds / 3600:.1f} ч"


def themed_embed(title: str, description: str = "", *, success: bool = False) -> discord.Embed:
    color = 0xFF3B47 if success else THEME_RED
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="RedCore • Black Edition")
    return embed
