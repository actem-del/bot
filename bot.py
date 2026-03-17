"""Compatibility launcher.

Запуск `python bot.py` теперь поднимает модульного бота из `discord-bot/main.py`,
чтобы работали все команды (profile/economy/leaderboard/admin), а не только /profile.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    modular_root = repo_root / "discord-bot"
    main_file = modular_root / "main.py"

    if not main_file.exists():
        raise RuntimeError("Не найден discord-bot/main.py")

    # Важно: cogs и utils импортируются как top-level пакеты из cwd.
    os.chdir(modular_root)
    sys.path.insert(0, str(modular_root))

    runpy.run_path(str(main_file), run_name="__main__")


if __name__ == "__main__":
    main()
