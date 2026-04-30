from database.db_manager import db

START_REQUIRED_TEXT = "Сначала напиши <code>старт</code>."


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


async def require_current_user(message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(START_REQUIRED_TEXT, parse_mode="HTML")
        return None
    await touch_current_user(message, user)
    return user


async def require_callback_user(callback):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала напиши старт", show_alert=True)
        return None
    await db.touch_user(callback.from_user.id)
    return user


async def get_active_cooldown_text(user_id, command, now, cooldowns_enabled=True) -> str | None:
    if not cooldowns_enabled:
        return None

    available_at = await db.get_cooldown(user_id, command)
    if available_at and available_at > now:
        return format_cooldown(int((available_at - now).total_seconds()))
    return None
