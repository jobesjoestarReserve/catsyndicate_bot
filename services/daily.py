import random
from datetime import date, timedelta

from database.db_manager import db

STREAK_SAVE_LIMIT = 3

DAILY_ACTION_MEOW = "meow"
DAILY_ACTION_HUNT = "hunt"
DAILY_ACTION_WORK = "work"
DAILY_ACTION_MINE = "mine"
DAILY_ACTION_CRAFT = "craft"
DAILY_ACTION_SHOP = "shop"
DAILY_ACTION_GROW = "grow"
DAILY_ACTION_BITE = "bite"
DAILY_ACTION_EVENT = "event"

DIFFICULTY_LABELS = {
    "easy": "лёгкие",
    "medium": "средние",
    "hard": "вкусные",
}

RESOURCE_LABELS = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}

TASK_POOL = {
    "easy": [
        {"id": "meow_easy", "title": "Стащить рыбов", "action": DAILY_ACTION_MEOW, "goal": 1},
        {"id": "hunt_easy", "title": "Поймать мышей", "action": DAILY_ACTION_HUNT, "goal": 1},
        {"id": "work_easy", "title": "Отправить мышей на работу", "action": DAILY_ACTION_WORK, "goal": 1},
        {"id": "mine_easy", "title": "Спустить мышей в подвал", "action": DAILY_ACTION_MINE, "goal": 1},
    ],
    "medium": [
        {"id": "meow_medium", "title": "Провернуть рыбный рейд", "action": DAILY_ACTION_MEOW, "goal": 2},
        {"id": "hunt_medium", "title": "Пополнить мышиную бригаду", "action": DAILY_ACTION_HUNT, "goal": 2},
        {"id": "work_medium", "title": "Закрыть смены мышей", "action": DAILY_ACTION_WORK, "goal": 2},
        {"id": "mine_medium", "title": "Накопать ресурсов", "action": DAILY_ACTION_MINE, "goal": 2},
        {"id": "craft_medium", "title": "Поторговаться с кузнецом", "action": DAILY_ACTION_CRAFT, "goal": 1},
        {"id": "shop_medium", "title": "Зайти в лавку расходников", "action": DAILY_ACTION_SHOP, "goal": 1},
    ],
    "hard": [
        {"id": "meow_hard", "title": "Провести рыбную операцию", "action": DAILY_ACTION_MEOW, "goal": 3},
        {"id": "hunt_hard", "title": "Собрать мышиный отдел кадров", "action": DAILY_ACTION_HUNT, "goal": 3},
        {"id": "mine_hard", "title": "Выжать подвал досуха", "action": DAILY_ACTION_MINE, "goal": 3},
        {"id": "craft_hard", "title": "Проверить характер кузницы", "action": DAILY_ACTION_CRAFT, "goal": 2},
        {"id": "shop_hard", "title": "Закупить подозрительные пузырьки", "action": DAILY_ACTION_SHOP, "goal": 2},
        {"id": "grow_hard", "title": "Попытаться вырасти", "action": DAILY_ACTION_GROW, "goal": 1},
        {"id": "bite_hard", "title": "Устроить дипломатический кусь", "action": DAILY_ACTION_BITE, "goal": 1},
        {"id": "event_hard", "title": "Влезть в чатовый хаос", "action": DAILY_ACTION_EVENT, "goal": 1},
    ],
}

DAILY_STREAK_SAVE_TEXTS = [
    "Секретарь Синдиката подложил в журнал липкую записку: «Кот был, просто драматично моргнул».",
    "Мышиный бухгалтер закрыл пропуск лапой и сказал, что это была техническая рыба.",
    "Кузнец случайно поставил печать «зачтено» раскалённой подковой. Спорить никто не рискнул.",
    "Дворовый арбитр решил, что отсутствие кота — это продвинутый стелс, а стелс надо уважать.",
    "Кот принес справку: «Был занят спасением дивана от экзистенциальной пустоты». Принято.",
    "Рыбный инспектор нашёл в протоколе селёдку и отвлёкся. Стрик незаметно выжил.",
    "Клановая канцелярия перепутала календарь с меню суши и засчитала день как очень вкусный.",
    "Мастер ежедневок уронил журнал в чай, а мокрые страницы всегда трактуются в пользу кота.",
    "Старший по мискам объявил пропуск тренировкой силы воли. Все сделали вид, что так и было.",
    "Ночная смена мышей подписала алиби лапками. Почерк ужасный, зато убедительный.",
    "Кот заявил, что проходил квест во сне. Комиссия проверила храп и нашла сюжет правдоподобным.",
    "Синдикат применил древний приём «ничего не было, разойдёмся». Стрик согласно кивнул.",
    "Рыбовоз опоздал, календарь покраснел от стыда и сам откатил штраф.",
    "Дежурный котик нажал большую кнопку «ну ладно» и сделал вид, что это часть регламента.",
    "Пропуск попытался сломать серию, но поскользнулся на рыбьей чешуе и улетел в архив.",
]


def get_daily_difficulty(streak_day: int) -> str:
    if streak_day <= 3:
        return "easy"
    if streak_day <= 9:
        return "medium"
    return "hard"


def get_streak_day_from_last_claim(last_claimed_date, last_streak_day: int, today: date) -> int:
    if last_claimed_date == today - timedelta(days=1):
        return last_streak_day + 1
    return 1


def get_streak_plan_from_last_claim(
    last_claimed_date,
    last_streak_day: int,
    saves_remaining: int | None,
    today: date,
) -> dict:
    saves_remaining = STREAK_SAVE_LIMIT if saves_remaining is None else max(0, saves_remaining)
    missed_days = (today - last_claimed_date).days - 1
    if missed_days <= 0:
        return {
            "streak_day": last_streak_day + 1,
            "saves_remaining": saves_remaining,
            "saved_missed_days": 0,
            "reset": False,
        }
    if missed_days <= saves_remaining:
        return {
            "streak_day": last_streak_day + 1,
            "saves_remaining": saves_remaining - missed_days,
            "saved_missed_days": missed_days,
            "reset": False,
        }
    return {
        "streak_day": 1,
        "saves_remaining": STREAK_SAVE_LIMIT,
        "saved_missed_days": 0,
        "reset": True,
    }


def _rng_for_daily(user_id: int, quest_date: date, difficulty: str):
    seed = f"{user_id}:{quest_date.isoformat()}:{difficulty}"
    return random.Random(seed)


def generate_daily_tasks(user_id: int, quest_date: date, streak_day: int) -> list[dict]:
    difficulty = get_daily_difficulty(streak_day)
    rng = _rng_for_daily(user_id, quest_date, difficulty)
    count = 2 if difficulty == "easy" else 3
    tasks = [dict(task, current=0) for task in rng.sample(TASK_POOL[difficulty], count)]
    return tasks


def generate_daily_reward(streak_day: int) -> dict:
    difficulty = get_daily_difficulty(streak_day)
    if difficulty == "easy":
        return {
            "fish": 25 + streak_day * 5,
            "items": [{"item_name": "trash", "item_type": "resource", "amount": 2}],
        }
    if difficulty == "medium":
        return {
            "fish": 70 + streak_day * 8,
            "items": [
                {"item_name": "wool", "item_type": "resource", "amount": 3},
                {"item_name": "trash", "item_type": "resource", "amount": 3},
            ],
        }
    return {
        "fish": 140 + streak_day * 12,
        "items": [
            {"item_name": "metal", "item_type": "resource", "amount": 4},
            {"item_name": "Кошачья мята", "item_type": "consumable", "amount": 1},
        ],
    }


def get_daily_save_text(user_id: int, quest_date: date, missed_days: int) -> str:
    seed = f"{user_id}:{quest_date.isoformat()}:save:{missed_days}"
    return random.Random(seed).choice(DAILY_STREAK_SAVE_TEXTS)


def apply_daily_action(tasks: list[dict], action: str, amount: int = 1) -> tuple[list[dict], bool]:
    changed = False
    updated = []
    for task in tasks:
        task = dict(task)
        if task["action"] == action and task["current"] < task["goal"]:
            task["current"] = min(task["goal"], task["current"] + amount)
            changed = True
        updated.append(task)
    return updated, changed


def are_daily_tasks_complete(tasks: list[dict]) -> bool:
    return bool(tasks) and all(task["current"] >= task["goal"] for task in tasks)


def format_daily_reward(reward: dict) -> str:
    lines = []
    if reward.get("fish"):
        lines.append(f"🐟 Рыбов: <b>{reward['fish']}</b>")
    for item in reward.get("items", []):
        amount = item["amount"]
        item_name = item["item_name"]
        label = RESOURCE_LABELS.get(item_name, item_name) if item.get("item_type") == "resource" else item_name
        lines.append(f"🎁 {label}: <b>{amount}</b>")
    return "\n".join(lines) if lines else "награда потерялась в бухгалтерии"


async def get_or_create_daily_state(user_id: int, quest_date: date | None = None):
    quest_date = quest_date or date.today()
    state = await db.get_daily_quest(user_id, quest_date)
    if state:
        return state

    last_claim = await db.get_latest_claimed_daily_quest(user_id, quest_date)
    if last_claim:
        streak_plan = get_streak_plan_from_last_claim(
            last_claim["quest_date"],
            last_claim["streak_day"],
            last_claim.get("streak_saves_remaining"),
            quest_date,
        )
        streak_day = streak_plan["streak_day"]
    else:
        streak_day = 1
        streak_plan = {
            "saves_remaining": STREAK_SAVE_LIMIT,
            "saved_missed_days": 0,
            "reset": False,
        }

    tasks = generate_daily_tasks(user_id, quest_date, streak_day)
    reward = generate_daily_reward(streak_day)
    save_text = ""
    if streak_plan["saved_missed_days"]:
        save_text = get_daily_save_text(user_id, quest_date, streak_plan["saved_missed_days"])
    return await db.create_daily_quest(
        user_id=user_id,
        quest_date=quest_date,
        difficulty=get_daily_difficulty(streak_day),
        streak_day=streak_day,
        streak_saves_remaining=streak_plan["saves_remaining"],
        saved_missed_days=streak_plan["saved_missed_days"],
        save_text=save_text,
        tasks=tasks,
        reward=reward,
    )


async def record_daily_action(user_id: int, action: str, amount: int = 1):
    state = await get_or_create_daily_state(user_id)
    if state["claimed"]:
        return state
    tasks, changed = apply_daily_action(state["tasks"], action, amount)
    if not changed:
        return state
    return await db.update_daily_quest_tasks(user_id, state["quest_date"], tasks)
