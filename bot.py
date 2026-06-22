# bot.py — Botning asosiy fayli, polling shu yerdan ishga tushiriladi

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import admin, user


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Admin routerini birinchi ulaymiz — shunda /admin, /add, /delete, /broadcast
    # kabi buyruqlar avval admin handlerlarga tushadi
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Bazani tayyorlab olamiz (jadvallar mavjud bo'lmasa yaratiladi)
    await init_db()

    # Eski (polling boshlanishidan oldingi) update larni tashlab yuboramiz
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
