import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

class DBManager:
    def __init__(self):
        self.url = os.getenv("DATABASE_URL")
        self.pool = None

    async def connect(self):
        if not self.pool:
            # Важно: используем create_pool для работы с acquire()
            self.pool = await asyncpg.create_pool(self.url)
            print("Пул подключений к БД создан")

    async def get_user(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    async def register_user(self, user_id, name):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, cat_name, life_stage, balance) VALUES ($1, $2, 1, 100)",
                user_id, name
            )

    async def update_balance(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)

    async def register_user(self, user_id, name):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, cat_name, life_stage, balance) VALUES ($1, $2, 1, 100)",
                user_id, name
            )

    async def get_top_cats(self, limit=5):
        async with self.pool.acquire() as conn:
            # Убедись, что здесь нет двойного async
            return await conn.fetch("SELECT cat_name, balance, life_stage FROM users ORDER BY balance DESC LIMIT $1", limit)
    
    async def delete_user(self, user_id):
        async with self.pool.acquire() as conn:
            # Удаляем пользователя. Связанные данные в других таблицах 
            # удалятся сами, если ты настраивал CASCADE в SQL, 
            # но пока просто грохнем юзера.
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
            print(f"Пользователь {user_id} удален из базы.")

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("Соединение с БД закрыто.")
        
db = DBManager()  # Готовый экземпляр для использования в других модулях