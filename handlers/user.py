# handlers/user.py — Oddiy foydalanuvchi uchun handlerlar
# Deep link orqali kino kodi qabul qilinadi, obuna tekshiriladi, kino yuboriladi

import asyncio
import html

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import database as db
from config import ADMIN_IDS
from keyboards.user_kb import (
    subscribe_keyboard,
    user_reply_keyboard,
    close_chat_keyboard,
    CHAT_BUTTON_TEXT,
    CLOSE_CHAT_BUTTON_TEXT,
)
from keyboards.admin_kb import admin_reply_keyboard

router = Router()


class ChatStates(StatesGroup):
    chatting = State()

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
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    """/start — avval obuna tekshiriladi, keyin (kod bo'lsa) kino yuboriladi"""
    user_id = message.from_user.id
    await state.clear()

    await db.add_user(telegram_id=user_id, username=message.from_user.username)

    is_admin = user_id in ADMIN_IDS
    reply_kb = admin_reply_keyboard() if is_admin else user_reply_keyboard()

    # Deep link parametrini ajratib olamiz: "/start 1234" -> "1234"
    args = message.text.split(maxsplit=1)
    code = args[1].strip() if len(args) > 1 else ""

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        if is_admin:
            await message.answer("🔧 Admin panel tugmasi yoqildi.", reply_markup=reply_kb)
        await ask_to_subscribe(message, code, missing)
        return

    if not code:
        await message.answer(welcome_text(message.from_user), reply_markup=reply_kb)
        return

    await handle_movie_code_request(message, bot, code)


@router.message(F.text == CHAT_BUTTON_TEXT)
async def start_admin_chat(message: Message, state: FSMContext):
    await state.set_state(ChatStates.chatting)
    await message.answer(
        "💬 Xabaringizni yozing, u adminga yuboriladi. Admin javobi shu yerga keladi.\n"
        "Chiqish uchun «❌ Chatni yopish» ni bosing.",
        reply_markup=close_chat_keyboard(),
    )


@router.message(StateFilter(ChatStates.chatting), F.text == CLOSE_CHAT_BUTTON_TEXT)
async def close_admin_chat(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Chat yopildi.", reply_markup=user_reply_keyboard())


@router.message(StateFilter(ChatStates.chatting))
async def forward_to_admins(message: Message, bot: Bot):
    user = message.from_user
    header = (
        f"💬 {html.escape(user.full_name)} "
        f"(@{user.username or '—'}, ID: {user.id}):\n"
        "↩️ Javob berish uchun shu xabarga reply qiling."
    )
    delivered = False
    for admin_id in ADMIN_IDS:
        try:
            header_msg = await bot.send_message(admin_id, header)
            copied = await bot.copy_message(
                chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            continue
        await db.save_chat_link(admin_id, header_msg.message_id, user.id)
        await db.save_chat_link(admin_id, copied.message_id, user.id)
        delivered = True

    await message.answer("✅ Adminga yuborildi." if delivered else "❌ Xabarni yuborib bo'lmadi.")


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
