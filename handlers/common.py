import random
from aiogram import Router, types, F
from aiogram.filters import Command
from database.db_manager import db  # Импортируем готовый экземпляр
from data.constants import MEOW_SUCCESS_TEXTS, MEOW_FAILURE_TEXTS, MEOW_SUCCESS_IMAGES, MEOW_FAILURE_IMAGES, CAT_STATUSES
router = Router()

@router.message(F.animation)
async def get_animation_id(message: types.Message):
    print(f"ID твоей гифки: {message.animation.file_id}")
    await message.answer(f"ID получен и выведен в консоль!")

# Не забудь импортировать F: from aiogram import F

@router.message(F.photo)
async def get_photo_id(message: types.Message):
    # Telegram присылает фото в нескольких размерах. Нам нужен самый большой.
    photo_id = message.photo[-1].file_id
    print(f"ID твоей картинки: {photo_id}")
    await message.answer(f"ID картинки получен!")

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await db.get_user(message.from_user.id)
    # Твой добытый file_id
    CATERPILLAR_ID = "CgACAgQAAxkBAAM_ae8C6qS_WOvOItIPpYjBzbQZrQ8AAk4ZAALdzQlS_ZW4sgFq3t47BA"

    if not user:
        await db.register_user(message.from_user.id, message.from_user.first_name)
        await message.answer_animation(
            animation=CATERPILLAR_ID,
            caption=(
                f"🐱Добро пожаловать в Синдикат!\n\n"
                f"Твой статус: {CAT_STATUSES[1]}\n"
                "Воруй рыбов через /meow и расти в иерархии."
            ),
            parse_mode="HTML"
        )
    else:
        status = CAT_STATUSES.get(user['life_stage'], "Ветеран")
        await message.answer(f"Мияу, {status} {user['cat_name']}!")

@router.message(Command("meow"))
async def cmd_meow(message: types.Message):
    user_id = message.from_user.id
    
    # 1. Проверяем кулдаун (как делали раньше)
    # ... твой код проверки времени ...

    # 2. Рандомим шанс (допустим 50/50 или зависит от уровня)
    is_success = random.random() < 0.5 

    if is_success:
        fish_caught = random.randint(5, 25) # Рандомное кол-во рыбов
        text = random.choice(MEOW_SUCCESS_TEXTS)
        image = random.choice(MEOW_SUCCESS_IMAGES)
        
        await db.update_balance(user_id, fish_caught)
        await message.answer_photo(
            photo=image,
            caption=f"{text}\n\n➕ Ты добыл <b>{fish_caught}</b> 🐟",
            parse_mode="HTML"
        )
    else:
        text = random.choice(MEOW_FAILURE_TEXTS)
        image = random.choice(MEOW_FAILURE_IMAGES)
        
        await message.answer_photo(
            photo=image,
            caption=f"{text}\n\n❌ В этот раз без добычи...",
            parse_mode="HTML"
        )

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if not user: return

    next_life_cost = user['life_stage'] * 500
    
    text = (
        f"📊 <b>ДОСЬЕ СИНДИКАТА</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 Кот: <code>{user['cat_name']}</code>\n"
        f"🐾 Жизнь: <b>{user['life_stage']}/9</b>\n"
        f"💰 Баланс: <b>{user['balance']} рыбов</b>\n"
        f"📈 Шанс кражи: <b>{10 + user['life_stage']*3}%</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💡 Следующая жизнь стоит: <code>{next_life_cost}</code> 🐟\n"
        f"Используй /upgrade чтобы стать круче."
    )
    # Здесь можно прикрепить ту самую крутую картинку Синдиката
    await message.answer(text, parse_mode="HTML")

@router.message(Command("reset_me"))
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли вообще кто-то
    user = await db.get_user(user_id)
    
    if user:
        await db.delete_user(user_id)
        await message.answer(
            "⚠️ <b>Профиль Синдиката аннигилирован!</b>\n"
            "Твои рыбы сгорели, а жизнь обнулилась. Пиши /start, чтобы начать с чистого листа.",
            parse_mode="HTML"
        )
    else:
        await message.answer("А тебя и так нет в списках Синдиката. Нечего удалять!")