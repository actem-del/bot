<<<<<<< HEAD
# bot
=======
# Discord Bot (modular)

Структура проекта:

```text
discord-bot/
│ main.py
│ config.py
│ database.py
│ requirements.txt
├─ cogs/
├─ utils/
├─ fonts/
├─ data/
└─ assets/
```

## Что реализовано

- ✔ система уровней
- ✔ XP за сообщения
- ✔ XP за голос
- ✔ экономика (balance, daily, pay)
- ✔ лидерборд
- ✔ красивые карточки профиля
- ✔ админ-команды
- ✔ магазин ролей

## Команды

- `/profile [user]` — карточка профиля
- `/balance [user]`, `/daily`, `/pay user amount`
- `/shop`, `/buy item_name`
- `/leaderboard [xp|coins|messages|voice_seconds]`
- `/admin_set_xp user xp`
- `/admin_add_coins user amount`
- `/admin_add_shop_role role price [item_name]`

## Запуск

```bash
cd discord-bot
pip install -r requirements.txt
export DISCORD_TOKEN="TOKEN"
# (опционально) для мгновенной синхронизации команд в тестовом сервере
export DISCORD_GUILD_ID="YOUR_GUILD_ID"
python main.py
```

## Важно

1. Включи в Discord Developer Portal intents:
   - Server Members Intent
   - Message Content Intent
2. Для красивых карточек добавь свои файлы:
   - `assets/background.png`
   - `assets/overlay.png`
   - шрифты `fonts/DejaVuSans.ttf`, `fonts/DejaVuSans-Bold.ttf`
3. `background.png` и `overlay.png` должны быть **валидными PNG** (если файл битый или не картинка — бот автоматически игнорирует его и берёт fallback фон).
4. Новые slash-команды глобально могут появляться до часа. Для мгновенного появления используй `DISCORD_GUILD_ID`.
>>>>>>> a28e6a1 (first commit)
