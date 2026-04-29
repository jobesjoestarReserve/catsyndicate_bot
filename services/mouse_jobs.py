import asyncio
import json
import logging
from datetime import datetime

from database.db_manager import db
from services.game_utils import format_cooldown

RESOURCE_NAMES = {
    "wool": "шерсть",
    "metal": "металл",
    "trash": "мусор",
}

MOUSE_JOB_CHECK_SECONDS = 10


def decode_payload(payload):
    if isinstance(payload, str):
        return json.loads(payload)
    return dict(payload)


def format_resources(resources):
    return "\n".join(
        f"{RESOURCE_NAMES.get(name, name).capitalize()}: <b>+{amount}</b>"
        for name, amount in resources.items()
        if amount > 0
    )


async def complete_work_job(bot, job, payload):
    resources = payload.get("resources") or {}
    authority = payload.get("authority") or 0
    result = await db.complete_mouse_work_job(
        job["id"],
        job["user_id"],
        payload["reward"],
        payload["mice_returned"],
        resources,
        authority,
    )
    if not result:
        return False

    lost = payload["mice_lost"]
    lost_text = (
        f"\nПотери бригады: <b>{lost}</b> 🐭"
        if lost
        else "\nБригада вернулась полностью, хотя часть мышей делает вид, что ничего не было."
    )
    resources_text = ""
    if resources:
        resources_text = "\nБонус-ресурсы: " + ", ".join(
            f"{RESOURCE_NAMES.get(name, name)} <b>+{amount}</b>"
            for name, amount in resources.items()
        )
    authority_text = f"\nАвторитет: <b>+{authority}</b>" if authority else ""
    buff_text = "\n🧪 Мышиный энергетик помог смене выжать больше рыбов." if payload.get("buff_used") else ""

    await bot.send_message(
        job["chat_id"],
        (
            f"{payload['title']}\n"
            f"{payload['result_text']}\n\n"
            f"Работа: <b>{payload['profile_label']}</b>\n"
            f"Отправлено: <b>{payload['mice_sent']}</b> 🐭\n"
            f"Добыто: <b>{payload['reward']}</b> 🐟"
            f"{lost_text}"
            f"{resources_text}"
            f"{authority_text}\n"
            f"Мышей дома: <b>{result['mice_count']}</b>\n"
            f"Баланс: <b>{result['balance']}</b> 🐟"
            f"{buff_text}"
        ),
        parse_mode="HTML",
    )
    return True


async def complete_mine_job(bot, job, payload):
    resources = payload.get("resources") or {}
    result = await db.complete_mice_mining_job(
        job["id"],
        job["user_id"],
        payload["mice_returned"],
        resources,
    )
    if not result:
        return False

    lost = payload["mice_lost"]
    lost_text = (
        f"\nНе вернулись из шахты: <b>{lost}</b> 🐭"
        if lost
        else "\nВсе добытчики вернулись, кроме чувства собственного достоинства."
    )
    resources_text = format_resources(resources)
    await bot.send_message(
        job["chat_id"],
        (
            "⛏️ Мыши вернулись из подвала и принесли крафтовую добычу.\n\n"
            f"{resources_text}\n"
            f"{lost_text}\n"
            f"Мышей дома: <b>{result['mice_count']}</b>"
        ),
        parse_mode="HTML",
    )
    return True


async def complete_due_mouse_jobs(bot, chat_id=None, user_id=None):
    jobs = await db.get_due_mouse_jobs(
        current_time=datetime.now(),
        chat_id=chat_id,
        user_id=user_id,
    )
    completed = 0
    for job in jobs:
        try:
            payload = decode_payload(job["payload"])
            if job["job_type"] == "work":
                completed += int(await complete_work_job(bot, job, payload))
            elif job["job_type"] == "mine":
                completed += int(await complete_mine_job(bot, job, payload))
        except Exception:
            logging.exception("Failed to complete mouse job %s", job["id"])
    return completed


async def mouse_job_loop(bot):
    while True:
        await complete_due_mouse_jobs(bot)
        await asyncio.sleep(MOUSE_JOB_CHECK_SECONDS)


def format_job_duration(seconds: int) -> str:
    return format_cooldown(max(1, seconds))
