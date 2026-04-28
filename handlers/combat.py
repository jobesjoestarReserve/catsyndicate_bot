import random
from datetime import datetime, timedelta
from html import escape

from aiogram import Router, types
from aiogram.filters import Command

from database.db_manager import db
from data.runtime_state import runtime_state
from data.texts import (
    BITE_LOSE_TEXTS,
    BITE_SELF_TEXTS,
    BITE_STALE_TARGET_TEXTS,
    BITE_WIN_TEXTS,
)
from services.game_utils import (
    format_cooldown,
    get_life_stage,
    get_telegram_cat_name,
    touch_current_user,
)

router = Router()

BITE_COMMAND = "bite"
BITE_ACTIVITY_WINDOW = timedelta(hours=2)

BITE_COOLDOWN_BY_LIFE = {
    1: 150,
    2: 140,
    3: 130,
    4: 115,
    5: 100,
    6: 90,
    7: 80,
    8: 70,
    9: 60,
}

def get_bite_cooldown(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    cooldown = BITE_COOLDOWN_BY_LIFE[life_stage]
    if cat_class == "assassin":
        cooldown -= 10
    return max(35, cooldown)


def get_bite_power(user) -> int:
    life_stage = get_life_stage(user)
    cat_class = user["cat_class"] or "none"
    power = random.randint(1, 3) + life_stage // 3
    if cat_class == "warrior":
        power += 1
    if cat_class == "assassin" and random.randint(1, 100) <= 25:
        power += 2
    return max(1, power)


def get_bite_chance(attacker, target) -> int:
    attacker_stage = get_life_stage(attacker)
    target_stage = get_life_stage(target)
    attacker_class = attacker["cat_class"] or "none"
    target_class = target["cat_class"] or "none"
    chance = 55 + (attacker_stage - target_stage) * 4
    if attacker_class == "assassin":
        chance += 8
    if attacker_class == "thief":
        chance += 4
    if target_class == "warrior":
        chance -= 7
    return max(20, min(85, chance))


@router.message(Command("bite"))
async def cmd_bite(message: types.Message):
    attacker_id = message.from_user.id
    attacker = await db.get_user(attacker_id)
    if not attacker:
        return await message.answer("Сначала /start")
    await touch_current_user(message, attacker)

    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.answer("Кусать надо ответом на сообщение: reply → <code>/bite</code>", parse_mode="HTML")

    target_telegram_user = message.reply_to_message.from_user
    target_id = target_telegram_user.id
    if target_telegram_user.is_bot:
        return await message.answer("Ботов кусать нельзя. У них вместо хвоста техподдержка.")
    if target_id == attacker_id:
        return await message.answer(random.choice(BITE_SELF_TEXTS))

    target = await db.get_user(target_id)
    if not target:
        return await message.answer("Жертва не числится в Синдикате. Пусть сначала напишет /start.")

    now = datetime.now()
    target_is_active = await db.is_user_recently_seen(
        target_id,
        int(BITE_ACTIVITY_WINDOW.total_seconds()),
    )
    if not target_is_active:
        return await message.answer(random.choice(BITE_STALE_TARGET_TEXTS))

    available_at = await db.get_cooldown(attacker_id, BITE_COMMAND)
    if runtime_state.cooldowns_enabled and available_at and available_at > now:
        remaining = int((available_at - now).total_seconds())
        cooldown_text = format_cooldown(remaining)
        return await message.answer(
            f"🦷 Зубы ещё остывают после прошлого дипломатического акта. Ждать: <b>{cooldown_text}</b>.",
            parse_mode="HTML"
        )

    attacker_name = escape(attacker["cat_name"] or get_telegram_cat_name(message))
    target_name = escape(target["cat_name"] or target_telegram_user.first_name or "цель")
    chance = get_bite_chance(attacker, target)
    success = random.randint(1, 100) <= chance

    if success:
        power = get_bite_power(attacker)
        target_mice = target["mice_count"] or 0
        target_balance = target["balance"] or 0
        mice_lost = min(target_mice, power)
        fish_lost = 0 if mice_lost else min(target_balance, random.randint(5, 12 + get_life_stage(attacker) * 2))
        stolen_fish = 0
        if (attacker["cat_class"] or "none") == "thief" and fish_lost:
            stolen_fish = max(1, fish_lost // 2)
        authority_gain = 2 + get_life_stage(attacker) // 3

        result = await db.apply_bite_result(
            attacker_id=attacker_id,
            target_id=target_id,
            attacker_mice_delta=0,
            attacker_fish_delta=stolen_fish,
            attacker_authority_delta=authority_gain,
            target_mice_delta=-mice_lost,
            target_fish_delta=-fish_lost,
            target_authority_delta=-1,
        )
        if runtime_state.cooldowns_enabled:
            await db.set_cooldown(attacker_id, BITE_COMMAND, now + timedelta(seconds=get_bite_cooldown(attacker)))

        loot_text = (
            f"Потери жертвы: <b>{mice_lost}</b> 🐭"
            if mice_lost
            else f"Мышей не было, поэтому пострадали рыбовы: <b>{fish_lost}</b> 🐟"
        )
        thief_text = f"\nГоп-налог: <b>{stolen_fish}</b> 🐟" if stolen_fish else ""
        return await message.answer(
            (
                f"🦷 <b>Кусь засчитан!</b>\n"
                f"{random.choice(BITE_WIN_TEXTS)}\n\n"
                f"{attacker_name} → {target_name}\n"
                f"{loot_text}{thief_text}\n"
                f"Авторитет: <b>+{authority_gain}</b>\n"
                f"Шанс укуса был: <b>{chance}%</b>\n\n"
                f"Твой авторитет: <b>{result['attacker']['authority']}</b>"
            ),
            parse_mode="HTML"
        )

    backlash = get_bite_power(target)
    attacker_mice = attacker["mice_count"] or 0
    attacker_balance = attacker["balance"] or 0
    mice_lost = min(attacker_mice, max(1, backlash // 2))
    fish_lost = 0 if mice_lost else min(attacker_balance, random.randint(3, 10 + get_life_stage(target)))
    authority_loss = 1
    result = await db.apply_bite_result(
        attacker_id=attacker_id,
        target_id=target_id,
        attacker_mice_delta=-mice_lost,
        attacker_fish_delta=-fish_lost,
        attacker_authority_delta=-authority_loss,
        target_mice_delta=0,
        target_fish_delta=0,
        target_authority_delta=1,
    )
    if runtime_state.cooldowns_enabled:
        await db.set_cooldown(attacker_id, BITE_COMMAND, now + timedelta(seconds=get_bite_cooldown(attacker)))

    loss_text = (
        f"Твои потери: <b>{mice_lost}</b> 🐭"
        if mice_lost
        else f"Мыши не прикрыли позор, списано: <b>{fish_lost}</b> 🐟"
    )
    await message.answer(
        (
            f"💢 <b>Кусь сорвался.</b>\n"
            f"{random.choice(BITE_LOSE_TEXTS)}\n\n"
            f"{attacker_name} → {target_name}\n"
            f"{loss_text}\n"
            f"Авторитет: <b>-{authority_loss}</b>\n"
            f"Шанс укуса был: <b>{chance}%</b>\n\n"
            f"Твой авторитет: <b>{result['attacker']['authority']}</b>"
        ),
        parse_mode="HTML"
    )


@router.message(Command("top"))
async def cmd_top(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if user:
        await touch_current_user(message, user)

    rows = await db.get_top_authority(10)
    if not rows:
        return await message.answer("Рейтинг пуст. Подворотня ждёт первого кусь-скандала.")

    lines = []
    for index, row in enumerate(rows, start=1):
        name = escape(row["cat_name"] or "Безымянный кот")
        lines.append(
            f"{index}. <b>{name}</b> — {row['authority'] or 0} авторитета, жизнь {row['life_stage']}/9"
        )

    await message.answer(
        "🏆 <b>Топ авторитета Синдиката</b>\n\n" + "\n".join(lines),
        parse_mode="HTML"
    )
