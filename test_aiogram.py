import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, User, Chat
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod

class MockSession(BaseSession):
    async def close(self):
        pass

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None):
        print(f"\n[BOT EXECUTES]: {method.__class__.__name__}")
        if hasattr(method, "text"):
            print(f"[BOT TESTO]: {method.text}")
        if hasattr(method, "caption") and method.caption:
            print(f"[BOT CAPTION]: {method.caption}")
        return None

async def main():
    bot = Bot(token="123456789:AAB", session=MockSession())
    dp = Dispatcher()

    @dp.message()
    async def handle(message: Message):
        await message.answer("Hello from mock!")

    user = User(id=123, is_bot=False, first_name="Test")
    chat = Chat(id=123, type="private")
    msg = Message(message_id=1, date=123, chat=chat, from_user=user, text="test")
    update = Update(update_id=1, message=msg)

    await dp.feed_update(bot, update)

if __name__ == "__main__":
    asyncio.run(main())
