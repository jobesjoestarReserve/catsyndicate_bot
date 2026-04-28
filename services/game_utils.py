from database.db_manager import db


def get_life_stage(user) -> int:
    return max(1, min(9, user["life_stage"]))


def get_telegram_cat_name(message) -> str:
    user = message.from_user
    if not user:
        return "Безымянный кот"
    return user.first_name or user.username or "Безымянный кот"


def is_broken_name(name) -> bool:
    if not name:
        return True
    text = str(name).strip()
    return bool(text) and set(text) == {"?"}


async def sync_cat_name_if_needed(message, user):
    telegram_name = get_telegram_cat_name(message)
    if is_broken_name(user["cat_name"]) or user["cat_name"] != telegram_name:
        await db.update_cat_name(message.from_user.id, telegram_name)
        return telegram_name
    return user["cat_name"]


async def touch_current_user(message, user=None):
    if not message.from_user:
        return user
    if user is None:
        user = await db.get_user(message.from_user.id)
    if user:
        await db.touch_user(message.from_user.id)
    return user


def format_cooldown(seconds: int) -> str:
    minutes, seconds = divmod(max(1, seconds), 60)
    if minutes:
        return f"{minutes} мин {seconds} сек"
    return f"{seconds} сек"
