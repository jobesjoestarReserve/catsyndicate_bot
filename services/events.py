import asyncio
import logging
import random
from datetime import datetime, timedelta

from data.runtime_state import runtime_state
from data.texts import (
    EVENT_BOSS_DEFEATED_TEXTS,
    EVENT_BOSS_EXPIRED_TEXTS,
    EVENT_SPAWN_TEXTS,
)
from database.db_manager import db
from services.game_utils import get_life_stage

logger = logging.getLogger(__name__)

EVENT_CHECK_SECONDS = 12 * 60
EVENT_ACTIVE_CHAT_SECONDS = 60 * 60
EVENT_AUTOSPAWN_CHANCE = 16
EVENT_CHAT_COOLDOWN_SECONDS = 2 * 60 * 60

EVENT_CONFIGS = {
    "boss": {
        "duration_seconds": 8 * 60,
        "hp_min": 65,
        "hp_max": 95,
        "reward_pool": 35,
        "wool_pool": 0,
        "metal_pool": 0,
        "trash_pool": 0,
        "weight": 35,
    },
    "fish_drop": {
        "duration_seconds": 5 * 60,
        "hp_min": 0,
        "hp_max": 0,
        "reward_pool": 170,
        "wool_pool": 0,
        "metal_pool": 0,
        "trash_pool": 0,
        "weight": 40,
    },
    "resource_drop": {
        "duration_seconds": 5 * 60,
        "hp_min": 0,
        "hp_max": 0,
        "reward_pool": 0,
        "wool_pool": 26,
        "metal_pool": 18,
        "trash_pool": 36,
        "weight": 25,
    },
}

RESOURCE_NAMES = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}


def normalize_event_type(event_type: str | None) -> str | None:
    aliases = {
        "boss": "boss",
        "dog": "boss",
        "mega_dog": "boss",
        "fish": "fish_drop",
        "fish_drop": "fish_drop",
        "resources": "resource_drop",
        "resource": "resource_drop",
        "res": "resource_drop",
        "resource_drop": "resource_drop",
    }
    return aliases.get((event_type or "").lower())


def choose_event_type() -> str:
    event_types = list(EVENT_CONFIGS.keys())
    weights = [EVENT_CONFIGS[event_type]["weight"] for event_type in event_types]
    return random.choices(event_types, weights=weights, k=1)[0]


def get_event_title(event_type: str) -> str:
    return {
        "boss": "Мега-пёс",
        "fish_drop": "Рыбный контейнер",
        "resource_drop": "Контейнер ресурсов",
    }.get(event_type, event_type)


def get_event_action(event_type: str) -> str:
    return "/bite_boss" if event_type == "boss" else "/grab"


def format_event_status(event) -> str:
    event_type = event["event_type"]
    if event_type == "boss":
        return (
            f"🐕 <b>{get_event_title(event_type)}</b>\n"
            f"HP: <b>{event['hp_current']}/{event['hp_max']}</b>\n"
            f"Команда: <code>/bite_boss</code>"
        )

    if event_type == "fish_drop":
        return (
            f"📦 <b>{get_event_title(event_type)}</b>\n"
            f"Рыбов осталось: <b>{event['reward_pool']}</b> 🐟\n"
            f"Команда: <code>/grab</code>"
        )

    resources = []
    for name in ("wool", "metal", "trash"):
        amount = event[f"{name}_pool"]
        if amount > 0:
            resources.append(f"{RESOURCE_NAMES[name]} <b>{amount}</b>")
    return (
        f"🧰 <b>{get_event_title(event_type)}</b>\n"
        f"Осталось: {', '.join(resources) if resources else '<b>пусто</b>'}\n"
        f"Команда: <code>/grab</code>"
    )


def format_spawn_message(event) -> str:
    text = random.choice(EVENT_SPAWN_TEXTS[event["event_type"]])
    return f"{text}\n\n{format_event_status(event)}"


async def spawn_chat_event(chat_id: int, event_type: str | None = None):
    event_type = normalize_event_type(event_type) or choose_event_type()
    config = EVENT_CONFIGS[event_type]
    hp_max = random.randint(config["hp_min"], config["hp_max"]) if event_type == "boss" else 0
    ends_at = datetime.now() + timedelta(seconds=config["duration_seconds"])
    return await db.create_chat_event(
        chat_id=chat_id,
        event_type=event_type,
        hp_max=hp_max,
        reward_pool=config["reward_pool"],
        wool_pool=config["wool_pool"],
        metal_pool=config["metal_pool"],
        trash_pool=config["trash_pool"],
        ends_at=ends_at,
    )


def roll_boss_damage(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    damage = random.randint(5, 9) + life_stage
    if cat_class == "warrior":
        damage += 2
    elif cat_class == "assassin":
        damage += random.randint(2, 5)
    elif cat_class == "support":
        damage = max(damage, 9 + life_stage)
    elif cat_class == "thief" and random.randint(1, 100) <= 25:
        damage += 3
    return damage


def roll_fish_grab(user) -> int:
    life_stage = get_life_stage(user)
    amount = random.randint(12, 22) + life_stage
    if (user["cat_class"] or "none") == "thief":
        amount += random.randint(2, 6)
    return amount


def roll_resource_grab(user) -> dict[str, int]:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    primary = random.choice(("wool", "metal", "trash"))
    resources = {primary: random.randint(3, 6) + life_stage // 3}
    if cat_class == "support":
        support_bonus = random.choice(("wool", "trash"))
        resources[support_bonus] = resources.get(support_bonus, 0) + 2
    if random.randint(1, 100) <= 35:
        extra = random.choice(("wool", "metal", "trash"))
        resources[extra] = resources.get(extra, 0) + random.randint(1, 3)
    return resources


async def reward_boss_if_defeated(event):
    if event["hp_current"] > 0:
        return None
    reward = event["reward_pool"]
    return await db.finish_boss_event(event["id"], reward, authority_reward=2)


async def expire_events(bot):
    for event in await db.get_expired_active_events():
        closed = await db.close_chat_event(event["id"], "expired")
        if not closed:
            continue
        await db.set_chat_event_cooldown(
            event["chat_id"],
            datetime.now() + timedelta(seconds=EVENT_CHAT_COOLDOWN_SECONDS),
        )
        if event["event_type"] == "boss":
            text = random.choice(EVENT_BOSS_EXPIRED_TEXTS)
        else:
            text = f"🕳 <b>{get_event_title(event['event_type'])} исчез.</b>\nКто успел, тот синдикат."
        try:
            await bot.send_message(event["chat_id"], text, parse_mode="HTML")
        except Exception:
            logger.exception("Failed to send expired event message to chat %s", event["chat_id"])


async def autospawn_loop(bot):
    while True:
        await asyncio.sleep(EVENT_CHECK_SECONDS)
        try:
            if not runtime_state.auto_events_enabled:
                continue
            await expire_events(bot)
            chats = await db.get_autospawn_candidate_chats(EVENT_ACTIVE_CHAT_SECONDS)
            for row in chats:
                if random.randint(1, 100) > EVENT_AUTOSPAWN_CHANCE:
                    continue
                event = await spawn_chat_event(row["chat_id"])
                if not event:
                    continue
                await db.set_chat_event_cooldown(
                    row["chat_id"],
                    datetime.now() + timedelta(seconds=EVENT_CHAT_COOLDOWN_SECONDS),
                )
                try:
                    await bot.send_message(
                        row["chat_id"],
                        format_spawn_message(event),
                        parse_mode="HTML",
                    )
                except Exception:
                    logger.exception("Failed to send spawned event message to chat %s", row["chat_id"])
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Autospawn loop failed")


def format_boss_defeated(result) -> str:
    participants = result["participants"]
    reward = result["event"]["reward_pool"]
    return (
        f"{random.choice(EVENT_BOSS_DEFEATED_TEXTS)}\n\n"
        f"Участников: <b>{len(participants)}</b>\n"
        f"Каждому: <b>{reward}</b> 🐟 и <b>+2</b> авторитета"
    )
