# Шерстяной Синдикат: Диаграмма Проекта

Эта диаграмма показывает, как проект собран на уровне архитектуры: от входящих Telegram-команд до хендлеров, сервисов и БД.

## Архитектура

```mermaid
flowchart TD
    TG["Telegram Chat / Users"] --> BOT["main.py<br/>Bot + Dispatcher + Polling"]
    BOT --> MW["services/activity.py<br/>ChatActivityMiddleware"]

    MW --> HC["handlers/common.py<br/>/start /meow /hunt /stats /reset_me"]
    MW --> HP["handlers/profile.py<br/>/profile"]
    MW --> HI["handlers/inventory.py<br/>/inv"]
    MW --> HM["handlers/mice.py<br/>/work /send_mice mine"]
    MW --> HCOMBAT["handlers/combat.py<br/>/bite /top"]
    MW --> HE["handlers/events.py<br/>/bite_boss /grab /event<br/>/spawn_event /events /end_event /events_auto"]
    MW --> HPROG["handlers/progression.py<br/>/grow /upgrade"]
    MW --> HA["handlers/admin.py<br/>/admin /cooldowns_on/off<br/>/add_fish /reset_fish"]

    HC --> GU["services/game_utils.py<br/>life helpers / cat name / cooldown text"]
    HP --> GU
    HM --> GU
    HCOMBAT --> GU
    HE --> GU
    HPROG --> GU

    HPROG --> SP["services/progression.py<br/>XP thresholds / cost / grow chance"]
    HE --> SE["services/events.py<br/>event config / autospawn / boss rewards"]

    HC --> TXT["data/texts.py<br/>reply pools"]
    HM --> TXT
    HCOMBAT --> TXT
    HE --> TXT
    HPROG --> TXT

    HC --> CONST["data/constants.py<br/>life titles / class labels"]
    HP --> CONST
    HPROG --> CONST

    BOT --> RS["data/runtime_state.py<br/>cooldowns_enabled / auto_events_enabled"]
    HC --> RS
    HM --> RS
    HCOMBAT --> RS
    HE --> RS
    HPROG --> RS
    HA --> RS

    BOT --> LOOP["services/events.py::autospawn_loop"]
    LOOP --> SE

    HC --> DB["database/db_manager.py"]
    HP --> DB
    HI --> DB
    HM --> DB
    HCOMBAT --> DB
    HE --> DB
    HPROG --> DB
    HA --> DB
    GU --> DB
    SE --> DB

    DB --> USERS["users<br/>profile / life_stage / life_xp / balance / mice / authority / last_seen"]
    DB --> INV["inventory<br/>resources / future items"]
    DB --> CD["cooldowns<br/>per-user command cooldowns"]
    DB --> CHAT["chat_activity<br/>chat activity + autospawn gate"]
    DB --> EVENTS["chat_events<br/>boss / fish_drop / resource_drop"]
    DB --> PARTS["event_participants<br/>damage / grabs"]
```

## Игровые Потоки

```mermaid
flowchart LR
    HUNT["/hunt"] --> MICE["mice_count"]
    MICE --> WORK["/work"]
    MICE --> MINE["/send_mice mine"]
    WORK --> FISH["balance / рыбов"]
    MINE --> RES["шерсть / металл / мусор"]
    FISH --> GROW["/grow"]
    GROW --> XP["life_xp"]
    XP --> LIFE["life_stage"]
    LIFE --> POWER["лучше шансы / меньше cooldown"]
    POWER --> HUNT
    POWER --> WORK
    POWER --> BITE["/bite"]
    POWER --> BOSS["/bite_boss"]
```

## События

```mermaid
flowchart TD
    TIMER["autospawn_loop"] --> ACTIVE{"чат активен?"}
    ACTIVE -- нет --> WAIT["ждать дальше"]
    ACTIVE -- да --> FREE{"нет активного события?"}
    FREE -- нет --> WAIT
    FREE -- да --> ROLL{"шанс спауна прошёл?"}
    ROLL -- нет --> WAIT
    ROLL -- да --> SPAWN["create_chat_event"]

    SPAWN --> BOSS["boss"]
    SPAWN --> FISH["fish_drop"]
    SPAWN --> RES["resource_drop"]

    BOSS --> HIT["/bite_boss"]
    HIT --> HP["hp_current"]
    HP --> REWARD["finish_boss_event"]

    FISH --> GRAB["/grab"]
    RES --> GRAB
    GRAB --> POOL["reward_pool / wool_pool / metal_pool / trash_pool"]
    POOL --> END["status completed or expired"]
```

## Где Это Смотреть В Коде

| Что | Файл |
|---|---|
| Запуск бота | `main.py` |
| Работа с БД | `database/db_manager.py` |
| Тексты и реплики | `data/texts.py` |
| Статусы жизней и классы | `data/constants.py` |
| Runtime-флаги | `data/runtime_state.py` |
| Утилиты игрока | `services/game_utils.py` |
| Логика роста | `services/progression.py` |
| Логика событий | `services/events.py` |
| Учёт активности чата | `services/activity.py` |
| Базовые команды | `handlers/common.py` |
| Профиль | `handlers/profile.py` |
| Инвентарь | `handlers/inventory.py` |
| Работа и шахта | `handlers/mice.py` |
| PvP | `handlers/combat.py` |
| События | `handlers/events.py` |
| Рост | `handlers/progression.py` |
| Админка | `handlers/admin.py` |
