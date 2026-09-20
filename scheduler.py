# scheduler.py — har kuni kunlik hisobot va bazaning avtomatik zaxirasini adminlarga yuboradi

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.types import FSInputFile

import database as db
from config import ADMIN_IDS, DB_NAME
from reports import daily_report

REPORT_HOUR = 9  # O'zbekiston vaqti bilan


async def send_daily(bot: Bot):
    text = await daily_report()
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
            await bot.send_document(
                admin_id, FSInputFile(DB_NAME), caption="🗄 Kunlik avtomatik zaxira"
            )
        except Exception:
            logging.exception("Kunlik hisobotni %s ga yuborib bo'lmadi", admin_id)


async def daily_job(bot: Bot):
    while True:
        current = db.now()
        run_at = current.replace(hour=REPORT_HOUR, minute=0, second=0, microsecond=0)
        if run_at <= current:
            run_at += timedelta(days=1)
        await asyncio.sleep((run_at - current).total_seconds())
        try:
            await send_daily(bot)
        except Exception:
            logging.exception("Kunlik ish xatosi")
