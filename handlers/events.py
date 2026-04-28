import random
from datetime import datetime, timedelta
from html import escape

from aiogram import Router, types
from aiogram.filters import Command

from data.runtime_state import runtime_state
from data.texts import EVENT_BOSS_HIT_TEXTS, EVENT_BUSY_TEXTS, EVENT_EMPTY_TEXTS, EVENT_GRAB_TEXTS
from database.db_manager import db
from handlers.admin import require_admin
from services.events import (
    EVENT_CHAT_COOLDOWN_SECONDS,
    RESOURCE_NAMES,
    format_boss_defeated,
    format_event_status,
    format_spawn_message,
    get_event_title,
    normalize_event_type,
    reward_boss_if_defeated,
    roll_boss_damage,
    roll_fish_grab,
    roll_resource_grab,
    spawn_chat_event,
)
from services.game_utils import format_cooldown, touch_current_user

router = Router()

BITE_BOSS_COMMAND = "bite_boss"
GRAB_COMMAND = "grab"
BITE_BOSS_COOLDOWN_SECONDS = 25
GRAB_COOLDOWN_SECONDS = 40


def get_args(message: types.Message) -> list[str]:
    return (message.text or "").split()[1:]


def format_resources(resources: dict[str, int]) -> str:
    return ", ".join(
        f"{RESOURCE_NAMES[name]} <b>+{amount}</b>"
        for name, amount in resources.items()
        if amount > 0
    )


def format_remaining_loot(event) -> str:
    if event["event_type"] == "fish_drop":
        return f"Осталось в контейнере: <b>{event['reward_pool']}</b> 🐟"

    resources = []
    for name in ("wool", "metal", "trash"):
        amount = event[f"{name}_pool"]
        if amount > 0:
            resources.append(f"{RESOURCE_NAMES[name]} <b>{amount}</b>")
    return "Осталось в контейнере: " + (", ".join(resources) if resources else "<b>пусто</b>")


@router.message(Command("bite_boss"))
async def cmd_bite_boss(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")
    await touch_current_user(message, user)

    event = await db.get_active_event(message.chat.id)
    if not event or event["event_type"] != "boss":
        return await message.answer("🐕 Босса во дворе нет. Можно кусать воздух, но авторитет не поймёт.")

    now = datetime.now()
    available_at = await db.get_cooldown(user_id, BITE_BOSS_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        cooldown_text = format_cooldown(int((available_at - now).total_seconds()))
        return await message.answer(
            f"🦷 Зубы перегрелись после прошлого героизма. Ждать: <b>{cooldown_text}</b>.",
            parse_mode="HTML",
        )

    damage = roll_boss_damage(user)
    result = await db.add_boss_damage(event["id"], user_id, damage)
    if not result:
        return await message.answer("🐾 Босс уже ушёл или спрятался за юридической формулировкой.")

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, BITE_BOSS_COMMAND, now + timedelta(seconds=BITE_BOSS_COOLDOWN_SECONDS))

    updated_event = result["event"]
    if updated_event["hp_current"] <= 0:
        defeated = await reward_boss_if_defeated(updated_event)
        if defeated:
            await db.set_chat_event_cooldown(
                message.chat.id,
                datetime.now() + timedelta(seconds=EVENT_CHAT_COOLDOWN_SECONDS),
            )
            return await message.answer(format_boss_defeated(defeated), parse_mode="HTML")

    name = escape(user["cat_name"] or message.from_user.first_name or "кот")
    await message.answer(
        (
            f"{random.choice(EVENT_BOSS_HIT_TEXTS)}\n\n"
            f"<b>{name}</b> нанёс <b>{damage}</b> урона.\n"
            f"HP босса: <b>{updated_event['hp_current']}/{updated_event['hp_max']}</b>"
        ),
        parse_mode="HTML",
    )


@router.message(Command("grab"))
async def cmd_grab(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return await message.answer("Сначала /start")
    await touch_current_user(message, user)

    event = await db.get_active_event(message.chat.id)
    if not event or event["event_type"] not in ("fish_drop", "resource_drop"):
        return await message.answer("📦 Контейнера нет. Есть только пол, воздух и сомнительная уверенность.")

    now = datetime.now()
    available_at = await db.get_cooldown(user_id, GRAB_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        cooldown_text = format_cooldown(int((available_at - now).total_seconds()))
        return await message.answer(
            f"🧤 Лапы заняты перевариванием добычи. Ждать: <b>{cooldown_text}</b>.",
            parse_mode="HTML",
        )

    fish = roll_fish_grab(user) if event["event_type"] == "fish_drop" else 0
    resources = roll_resource_grab(user) if event["event_type"] == "resource_drop" else {}
    result = await db.grab_event_loot(event["id"], user_id, fish, resources)
    if not result:
        return await message.answer("📦 Контейнер уже испарился из бухгалтерии Синдиката.")
    if result["empty"]:
        return await message.answer(random.choice(EVENT_EMPTY_TEXTS))

    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(user_id, GRAB_COMMAND, now + timedelta(seconds=GRAB_COOLDOWN_SECONDS))

    loot = []
    if result["fish"]:
        loot.append(f"<b>+{result['fish']}</b> 🐟")
    if result["resources"]:
        loot.append(format_resources(result["resources"]))

    closed_text = ""
    if result["event"]["status"] == "completed":
        closed_text = "\n\n🏁 Контейнер вычищен до состояния музейного экспоната."
        await db.set_chat_event_cooldown(
            message.chat.id,
            datetime.now() + timedelta(seconds=EVENT_CHAT_COOLDOWN_SECONDS),
        )

    await message.answer(
        (
            f"{random.choice(EVENT_GRAB_TEXTS)}\n\n"
            f"Добыча: {'; '.join(loot)}"
            f"\n{format_remaining_loot(result['event'])}"
            f"{closed_text}"
        ),
        parse_mode="HTML",
    )


@router.message(Command("spawn_event"))
async def cmd_spawn_event(message: types.Message):
    if not await require_admin(message):
        return

    args = get_args(message)
    event_type = normalize_event_type(args[0] if args else None)
    if not event_type:
        return await message.answer(
            "Формат: <code>/spawn_event boss</code>, <code>/spawn_event fish</code> или <code>/spawn_event resources</code>.",
            parse_mode="HTML",
        )

    event = await spawn_chat_event(message.chat.id, event_type)
    if not event:
        return await message.answer(random.choice(EVENT_BUSY_TEXTS))

    await message.answer(format_spawn_message(event), parse_mode="HTML")


@router.message(Command("events"))
async def cmd_events(message: types.Message):
    if not await require_admin(message):
        return

    rows = await db.list_active_events()
    if not rows:
        return await message.answer("📭 Активных событий нет. Двор подозрительно спокоен.")

    lines = []
    for event in rows:
        lines.append(
            f"#{event['id']} chat <code>{event['chat_id']}</code>: <b>{get_event_title(event['event_type'])}</b>"
        )
    await message.answer("📋 <b>Активные события</b>\n\n" + "\n".join(lines), parse_mode="HTML")


@router.message(Command("event"))
async def cmd_event(message: types.Message):
    event = await db.get_active_event(message.chat.id)
    if not event:
        return await message.answer("📭 Сейчас в чате нет активного события.")
    await message.answer(format_event_status(event), parse_mode="HTML")


@router.message(Command("end_event"))
async def cmd_end_event(message: types.Message):
    if not await require_admin(message):
        return

    event = await db.get_active_event(message.chat.id)
    if not event:
        return await message.answer("📭 В этом чате нечего закрывать.")

    await db.close_chat_event(event["id"], "cancelled")
    await db.set_chat_event_cooldown(
        message.chat.id,
        datetime.now() + timedelta(seconds=EVENT_CHAT_COOLDOWN_SECONDS),
    )
    await message.answer(f"🧹 Событие <b>{get_event_title(event['event_type'])}</b> закрыто.", parse_mode="HTML")


@router.message(Command("events_auto"))
async def cmd_events_auto(message: types.Message):
    if not await require_admin(message):
        return

    args = get_args(message)
    if not args or args[0].lower() not in ("on", "off"):
        state = "включён" if runtime_state.auto_events_enabled else "выключен"
        return await message.answer(
            f"Автоспаун сейчас: <b>{state}</b>.\nФормат: <code>/events_auto on</code> или <code>/events_auto off</code>.",
            parse_mode="HTML",
        )

    enabled = args[0].lower() == "on"
    runtime_state.auto_events_enabled = enabled
    state = "включён" if enabled else "выключен"
    await message.answer(f"✅ Глобальный автоспаун событий {state}.")
