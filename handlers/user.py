# handlers/user.py — Oddiy foydalanuvchi uchun handlerlar
# Deep link orqali kino kodi qabul qilinadi, obuna tekshiriladi, kino yuboriladi

import asyncio
import html

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import database as db
from config import ADMIN_IDS
from keyboards.user_kb import subscribe_keyboard
from keyboards.admin_kb import admin_reply_keyboard

router = Router()

def welcome_text(user) -> str:
    return (
        f"👋 Salom, {html.escape(user.full_name)}! "
        "Kino kodini yuboring yoki kino kodini o'z ichiga olgan havoladan foydalaning."
    )


_delete_tasks: set[asyncio.Task] = set()


async def delete_later(bot: Bot, chat_id: int, message_id: int, seconds: int):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


async def get_unsubscribed_channels(bot: Bot, user_id: int):
    """Foydalanuvchi obuna bo'lmagan majburiy kanallar ro'yxati (bo'sh bo'lsa — hammasiga obuna)"""
    missing = []
    for channel in await db.get_channels():
        _, chat_id, _, _ = channel
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            subscribed = member.status not in ("left", "kicked")
        except (TelegramBadRequest, TelegramForbiddenError):
            subscribed = False
        if not subscribed:
            missing.append(channel)
    return missing


async def ask_to_subscribe(message: Message, code: str, channels):
    await message.answer(
        "📢 Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
        reply_markup=subscribe_keyboard(code, channels),
    )


async def send_movie_to_user(bot: Bot, user_id: int, code: str) -> bool:
    """Berilgan kod bo'yicha kinoni topib foydalanuvchiga yuboradi.
    Topilmasa False qaytaradi"""
    movie = await db.get_movie_by_code(code)
    if movie is None:
        return False

    _, file_id, file_type, name = movie
    minutes = await db.get_delete_minutes()
    caption = f"🎬 {name}"
    if minutes > 0:
        caption += (
            f"\n\n⚠️ Mualliflik huquqi sababli bu kino {minutes} daqiqadan keyin o'chiriladi. "
            "Iltimos, uni hoziroq «Saqlangan xabarlar» (Saved Messages) ga yoki qurilmangizga saqlab oling."
        )
    if file_type == "document":
        sent = await bot.send_document(chat_id=user_id, document=file_id, caption=caption)
    else:
        sent = await bot.send_video(chat_id=user_id, video=file_id, caption=caption)

    if minutes > 0:
        task = asyncio.create_task(delete_later(bot, user_id, sent.message_id, minutes * 60))
        _delete_tasks.add(task)
        task.add_done_callback(_delete_tasks.discard)

    await db.add_request(user_id=user_id, movie_code=code)
    return True


async def handle_movie_code_request(message: Message, bot: Bot, code: str):
    """Berilgan kino kodi bo'yicha obunani tekshiradi va kinoni yuboradi"""
    user_id = message.from_user.id

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        await ask_to_subscribe(message, code, missing)
        return

    sent = await send_movie_to_user(bot, user_id, code)
    if not sent:
        await message.answer("❌ Bunday kodli kino topilmadi.")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """/start — avval obuna tekshiriladi, keyin (kod bo'lsa) kino yuboriladi"""
    user_id = message.from_user.id

    await db.add_user(telegram_id=user_id, username=message.from_user.username)

    reply_kb = admin_reply_keyboard() if user_id in ADMIN_IDS else None

    # Deep link parametrini ajratib olamiz: "/start 1234" -> "1234"
    args = message.text.split(maxsplit=1)
    code = args[1].strip() if len(args) > 1 else ""

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        if reply_kb:
            await message.answer("🔧 Admin panel tugmasi yoqildi.", reply_markup=reply_kb)
        await ask_to_subscribe(message, code, missing)
        return

    if not code:
        await message.answer(welcome_text(message.from_user), reply_markup=reply_kb)
        return

    await handle_movie_code_request(message, bot, code)


@router.message(F.text, ~F.text.startswith("/"))
async def handle_plain_text_code(message: Message, bot: Bot):
    """Buyruq bo'lmagan har qanday matn kino kodi sifatida qaraladi"""
    code = message.text.strip()
    if not code:
        return

    await db.add_user(telegram_id=message.from_user.id, username=message.from_user.username)
    await handle_movie_code_request(message, bot, code)


@router.callback_query(F.data.startswith("check_sub:"))
async def callback_check_subscription(callback: CallbackQuery, bot: Bot):
    """'Obunani tekshirish' tugmasi bosilganda ishlaydi"""
    user_id = callback.from_user.id
    code = callback.data.split(":", maxsplit=1)[1]

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=subscribe_keyboard(code, missing))
        return

    await callback.message.delete()
    if not code:
        await callback.message.answer(welcome_text(callback.from_user))
        await callback.answer("✅ Obuna tasdiqlandi!")
        return

    sent = await send_movie_to_user(bot, user_id, code)
    if sent:
        await callback.answer("✅ Obuna tasdiqlandi!")
    else:
        await callback.message.answer("❌ Bunday kodli kino topilmadi.")
        await callback.answer()
