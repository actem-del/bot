from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    token: str
    prefix: str = "!"
    daily_reward: int = 100


def get_settings() -> Settings:
    token = os.environ.get("DISCORD_TOKEN")
    print("DISCORD_TOKEN exists:", bool(token))

    if not token:
        raise RuntimeError("Укажите DISCORD_TOKEN в переменной окружения")

    return Settings(
        token=token,
        prefix=os.environ.get("BOT_PREFIX", "!"),
        daily_reward=int(os.environ.get("DAILY_REWARD", "100")),
    )