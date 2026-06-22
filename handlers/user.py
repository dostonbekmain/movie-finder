# handlers/user.py — Oddiy foydalanuvchi uchun handlerlar
# Deep link orqali kino kodi qabul qilinadi, obuna tekshiriladi, kino yuboriladi

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

import database as db
from config import PUBLIC_CHANNEL_USERNAME, ADMIN_IDS
from keyboards.user_kb import subscribe_keyboard
from keyboards.admin_kb import admin_reply_keyboard

router = Router()


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi PUBLIC kanalga obuna bo'lganini tekshiradi"""
    try:
        member = await bot.get_chat_member(chat_id=f"@{PUBLIC_CHANNEL_USERNAME}", user_id=user_id)
        # 'left' va 'kicked' obuna bo'lmaganlikni bildiradi
        return member.status not in ("left", "kicked")
    except TelegramBadRequest:
        # Foydalanuvchi kanalda umuman bo'lmagan bo'lishi mumkin
        return False


async def send_movie_to_user(message_or_callback, bot: Bot, user_id: int, code: str) -> bool:
    """Berilgan kod bo'yicha kinoni topib foydalanuvchiga yuboradi.
    Topilmasa False qaytaradi"""
    movie = await db.get_movie_by_code(code)
    if movie is None:
        return False

    _, file_id, file_type, name = movie
    if file_type == "document":
        await bot.send_document(chat_id=user_id, document=file_id, caption=f"🎬 {name}")
    else:
        await bot.send_video(chat_id=user_id, video=file_id, caption=f"🎬 {name}")

    await db.add_request(user_id=user_id, movie_code=code)
    return True


async def handle_movie_code_request(message: Message, bot: Bot, code: str):
    """Berilgan kino kodi bo'yicha obunani tekshiradi va kinoni yuboradi.
    Deep link (/start <kod>) va oddiy matn (foydalanuvchi kodni qo'lda yozsa)
    uchun umumiy mantiq"""
    user_id = message.from_user.id

    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        await message.answer(
            "📢 Botdan foydalanish uchun avval kanalga obuna bo'ling.",
            reply_markup=subscribe_keyboard(code),
        )
        return

    sent = await send_movie_to_user(message, bot, user_id, code)
    if not sent:
        await message.answer("❌ Bunday kodli kino topilmadi.")


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Foydalanuvchi botga /start bosganda ishlaydi.
    Agar deep link orqali kino kodi kelgan bo'lsa (masalan /start 1234),
    obuna tekshiriladi va kino yuboriladi"""
    user_id = message.from_user.id
    username = message.from_user.username

    # Foydalanuvchini bazaga qo'shamiz (agar mavjud bo'lmasa)
    await db.add_user(telegram_id=user_id, username=username)

    # Admin bo'lsa, pastda doimiy "Admin panel" tugmasi chiqib turadi
    reply_kb = admin_reply_keyboard() if user_id in ADMIN_IDS else None

    # Deep link parametrini ajratib olamiz: "/start 1234" -> "1234"
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        # Kino kodi yo'q — oddiy foydalanuvchi uchun boshqa menyu yo'q
        await message.answer(
            "👋 Salom! Kino kodini yuboring yoki kino kodini o'z ichiga olgan havoladan foydalaning.",
            reply_markup=reply_kb,
        )
        return

    code = args[1].strip()
    await handle_movie_code_request(message, bot, code)


@router.message(F.text, ~F.text.startswith("/"))
async def handle_plain_text_code(message: Message, bot: Bot):
    """Foydalanuvchi kino kodini to'g'ridan-to'g'ri matn sifatida yuborsa
    (deep link siz), buyruq bo'lmagan har qanday matn kino kodi sifatida qaraladi"""
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

    is_subscribed = await check_subscription(bot, user_id)
    if not is_subscribed:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmagansiz!", show_alert=True)
        return

    sent = await send_movie_to_user(callback, bot, user_id, code)
    if sent:
        await callback.message.delete()
        await callback.answer("✅ Obuna tasdiqlandi!")
    else:
        await callback.answer("❌ Bunday kodli kino topilmadi.", show_alert=True)
