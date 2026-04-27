import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# 1. Импортируем базу
from database.db_manager import db

# 2. Импортируем роутеры под уникальными именами
from handlers.common import router as common_router
from handlers.profile import router as profile_router
from handlers.inventory import router as inv_router

load_dotenv()

async def main():
    logging.basicConfig(level=logging.INFO)

    # Подключаем базу
    await db.connect()

    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()

    # 3. Регистрируем каждый роутер строго ОДИН раз
    dp.include_router(common_router)
    dp.include_router(profile_router)
    dp.include_router(inv_router)

    print("--- СИНДИКАТ ЗАПУЩЕН И БАЗА ГОТОВА ---")
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n--- СИНДИКАТ УШЕЛ В ТЕНЬ (Бот остановлен) ---")