# Шерстяной Синдикат

Telegram-бот с игровой петлей про рыбов, мышей, рост по девяти жизням, PvP и чатовые события.

## Быстрый старт

1. Установи Python 3.11+.
2. Создай свежее окружение:

```powershell
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Если `py` не установлен, используй полный путь к своему `python.exe`:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Подними PostgreSQL:

```powershell
docker compose up -d db
```

4. Создай `.env`:

```text
BOT_TOKEN=telegram_bot_token
DATABASE_URL=postgresql://postgres:cats_secret_password@localhost:5432/catsyndicate
```

5. Запусти бота:

```powershell
.\venv\Scripts\python.exe main.py
```

`venv` не хранится в git и может ломаться при переносе проекта между пользователями или машинами. Если окружение ссылается на несуществующий Python, проще удалить папку `venv` и создать её заново командами выше.

## Документация

- [Архитектурная диаграмма](docs/project_diagram.md)
- [Mind map проекта](docs/project_mind_map.md)

База данных инициализируется при старте через `database/db_manager.py::ensure_schema`: код создаёт базовые таблицы и добавляет недостающие колонки для текущей версии проекта.
