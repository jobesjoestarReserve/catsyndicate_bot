from aiogram import BaseMiddleware

from database.db_manager import db


class ChatActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        chat = getattr(event, "chat", None)
        if chat:
            await db.touch_chat(chat.id)
        return await handler(event, data)
