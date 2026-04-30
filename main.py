import asyncio
import contextlib
import os
import logging
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# 1. Импортируем базу
from database.db_manager import db

# 2. Импортируем роутеры под уникальными именами
from handlers.common import router as common_router
from handlers.combat import router as combat_router
from handlers.crafting import router as crafting_router
from handlers.events import router as events_router
from handlers.daily import router as daily_router
from handlers.mice import router as mice_router
from handlers.progression import router as progression_router
from handlers.profile import router as profile_router
from handlers.inventory import router as inv_router
from handlers.admin import router as admin_router
from handlers.shop import router as shop_router
from services.activity import ChatActivityMiddleware
from services.events import autospawn_loop
from services.mouse_jobs import mouse_job_loop

load_dotenv()

async def main():
    logging.basicConfig(level=logging.INFO)

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env before starting the bot.")
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set. Add it to .env before starting the bot.")

    # Подключаем базу
    await db.connect()

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(ChatActivityMiddleware())

    # 3. Регистрируем каждый роутер строго ОДИН раз
    dp.include_router(common_router)
    dp.include_router(combat_router)
    dp.include_router(crafting_router)
    dp.include_router(events_router)
    dp.include_router(daily_router)
    dp.include_router(mice_router)
    dp.include_router(progression_router)
    dp.include_router(profile_router)
    dp.include_router(inv_router)
    dp.include_router(shop_router)
    dp.include_router(admin_router)

    print("--- СИНДИКАТ ЗАПУЩЕН И БАЗА ГОТОВА ---")
    
    autospawn_task = asyncio.create_task(autospawn_loop(bot))
    mouse_job_task = asyncio.create_task(mouse_job_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        autospawn_task.cancel()
        mouse_job_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await autospawn_task
        with contextlib.suppress(asyncio.CancelledError):
            await mouse_job_task
        await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- СИНДИКАТ УШЕЛ В ТЕНЬ (Бот остановлен) ---")
