from aiogram import Router, types
from aiogram.filters import Command

from data.runtime_state import runtime_state
from database.db_manager import db

router = Router()

ADMIN_USER_IDS = {726768206}


def is_admin(message: types.Message) -> bool:
    return message.from_user and message.from_user.id in ADMIN_USER_IDS


async def require_admin(message: types.Message) -> bool:
    if is_admin(message):
        return True
    await message.answer("⛔ Нет доступа.")
    return False


def get_args(message: types.Message) -> list[str]:
    return (message.text or "").split()[1:]


def parse_int(value: str):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_target_user_id(message: types.Message, args: list[str]):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, args

    if args:
        maybe_user_id = parse_int(args[0])
        if maybe_user_id and len(args) > 1:
            return maybe_user_id, args[1:]

    return message.from_user.id, args


def resolve_target_user_id_only(message: types.Message, args: list[str]):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, args

    if args:
        maybe_user_id = parse_int(args[0])
        if maybe_user_id:
            return maybe_user_id, args[1:]

    return message.from_user.id, args


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not await require_admin(message):
        return

    cooldowns = "включены" if runtime_state.cooldowns_enabled else "выключены"
    auto_events = "включён" if runtime_state.auto_events_enabled else "выключен"
    await message.answer(
        (
            "🛠 <b>Админ-панель Синдиката</b>\n\n"
            f"Cooldown-ы: <b>{cooldowns}</b>\n"
            f"Автоспаун событий: <b>{auto_events}</b>\n\n"
            "<code>/cooldowns_on</code> — включить cooldown-ы\n"
            "<code>/cooldowns_off</code> — выключить cooldown-ы\n"
            "<code>/spawn_event boss</code> — запустить Мега-пса\n"
            "<code>/spawn_event fish</code> — сбросить рыбный контейнер\n"
            "<code>/spawn_event resources</code> — сбросить ресурсный контейнер\n"
            "<code>/events</code> — список активных событий\n"
            "<code>/event</code> — событие в текущем чате\n"
            "<code>/end_event</code> — закрыть событие в текущем чате\n"
            "<code>/events_auto on/off</code> — глобальный автоспаун\n"
            "<code>/add_fish 100</code> — добавить рыбов себе\n"
            "<code>/add_fish USER_ID 100</code> — добавить рыбов игроку\n"
            "<code>/reset_fish</code> — обнулить рыбов себе\n"
            "<code>/reset_fish USER_ID</code> — обнулить рыбов игроку\n\n"
            "Можно использовать <code>/add_fish 100</code> или <code>/reset_fish</code> ответом на сообщение игрока."
        ),
        parse_mode="HTML",
    )


@router.message(Command("cooldowns_on"))
async def cmd_cooldowns_on(message: types.Message):
    if not await require_admin(message):
        return

    runtime_state.cooldowns_enabled = True
    await message.answer("✅ Cooldown-ы включены.")


@router.message(Command("cooldowns_off"))
async def cmd_cooldowns_off(message: types.Message):
    if not await require_admin(message):
        return

    runtime_state.cooldowns_enabled = False
    await message.answer("🧪 Cooldown-ы выключены. Можно тестировать без ожидания.")


@router.message(Command("add_fish"))
async def cmd_add_fish(message: types.Message):
    if not await require_admin(message):
        return

    target_user_id, args = resolve_target_user_id(message, get_args(message))
    amount = parse_int(args[0]) if args else None
    if amount is None or amount <= 0:
        await message.answer(
            "Формат: <code>/add_fish 100</code> или <code>/add_fish USER_ID 100</code>. Сумма должна быть больше нуля.",
            parse_mode="HTML",
        )
        return

    user = await db.get_user(target_user_id)
    if not user:
        await message.answer("Игрок не найден в базе. Пусть сначала напишет /start.")
        return

    balance = await db.update_balance(target_user_id, amount)
    await message.answer(
        f"✅ Игроку <code>{target_user_id}</code> добавлено <b>{amount}</b> 🐟.\n"
        f"Баланс теперь: <b>{balance}</b> 🐟",
        parse_mode="HTML",
    )


@router.message(Command("reset_fish"))
async def cmd_reset_fish(message: types.Message):
    if not await require_admin(message):
        return

    target_user_id, args = resolve_target_user_id_only(message, get_args(message))
    if args:
        await message.answer("Формат: <code>/reset_fish</code> или <code>/reset_fish USER_ID</code>", parse_mode="HTML")
        return

    user = await db.get_user(target_user_id)
    if not user:
        await message.answer("Игрок не найден в базе. Пусть сначала напишет /start.")
        return

    balance = await db.set_balance(target_user_id, 0)
    await message.answer(
        f"🧹 Рыбов у игрока <code>{target_user_id}</code> обнулено.\n"
        f"Баланс теперь: <b>{balance}</b> 🐟",
        parse_mode="HTML",
    )
