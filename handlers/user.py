# handlers/user.py — Oddiy foydalanuvchi uchun handlerlar
# Kino kodi/nomi bo'yicha qidirish, obuna tekshiruvi, janrlar, sevimlilar, referal, admin bilan chat

import asyncio
import html

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import database as db
from config import ADMIN_IDS, BOT_USERNAME, GENRES
from texts import t, all_texts
from keyboards.user_kb import (
    PAGE_SIZE,
    subscribe_keyboard,
    user_reply_keyboard,
    close_chat_keyboard,
    movie_keyboard,
    movie_list_keyboard,
    genres_keyboard,
    lang_keyboard,
)
from keyboards.admin_kb import admin_reply_keyboard

router = Router()

_delete_tasks: set[asyncio.Task] = set()


class ChatStates(StatesGroup):
    chatting = State()


# ---------------------- Yordamchi funksiyalar ----------------------

def main_keyboard(user_id: int, lang: str):
    return admin_reply_keyboard() if user_id in ADMIN_IDS else user_reply_keyboard(lang)


def welcome_text(user, lang: str) -> str:
    return t(lang, "welcome", name=html.escape(user.full_name))


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


async def ask_to_subscribe(message: Message, code: str, channels, lang: str):
    await message.answer(
        t(lang, "subscribe"), reply_markup=subscribe_keyboard(code, channels, lang)
    )


async def build_movie_kb(user_id: int, code: str, part: int):
    parts = await db.get_parts_count(code)
    likes, dislikes = await db.get_rating_counts(code)
    is_fav = await db.is_favorite(user_id, code)
    return movie_keyboard(code, part, parts, likes, dislikes, is_fav)


async def send_movie_part(bot: Bot, user_id: int, code: str, part: int, lang: str) -> bool:
    """Kinoning berilgan qismini yuboradi (1 — asosiy fayl). Topilmasa False"""
    movie = await db.get_movie_by_code(code)
    if movie is None:
        return False

    _, file_id, file_type, name = movie
    if part > 1:
        episode = await db.get_episode(code, part)
        if episode is None:
            return False
        file_id, file_type = episode

    parts = await db.get_parts_count(code)
    minutes = await db.get_delete_minutes()
    caption = f"🎬 {html.escape(name)}"
    if parts > 1:
        caption += f" — {part}/{parts}"
    if minutes > 0:
        caption += "\n\n" + t(lang, "copyright", minutes=minutes)

    keyboard = await build_movie_kb(user_id, code, part)
    if file_type == "document":
        sent = await bot.send_document(
            chat_id=user_id, document=file_id, caption=caption, reply_markup=keyboard
        )
    else:
        sent = await bot.send_video(
            chat_id=user_id, video=file_id, caption=caption, reply_markup=keyboard
        )

    if minutes > 0:
        task = asyncio.create_task(delete_later(bot, user_id, sent.message_id, minutes * 60))
        _delete_tasks.add(task)
        task.add_done_callback(_delete_tasks.discard)

    if part == 1:
        await db.add_request(user_id=user_id, movie_code=code)
    return True


async def deliver_movie(message: Message, bot: Bot, user_id: int, code: str, part: int = 1) -> bool:
    """Obunani tekshiradi va kinoni yuboradi. Obuna yo'q bo'lsa, obuna so'raydi (False qaytaradi)"""
    lang = await db.get_lang(user_id)
    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        await ask_to_subscribe(message, code, missing, lang)
        return False
    sent = await send_movie_part(bot, user_id, code, part, lang)
    if not sent:
        await message.answer(t(lang, "not_found"))
    return sent


async def handle_movie_code_request(message: Message, bot: Bot, code: str):
    """Kod bo'yicha kino yuboradi; kod topilmasa — nom bo'yicha qidiradi"""
    user_id = message.from_user.id
    lang = await db.get_lang(user_id)

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        await ask_to_subscribe(message, code, missing, lang)
        return

    if await send_movie_part(bot, user_id, code, 1, lang):
        return

    results = await db.search_movies(code, limit=10)
    if not results:
        await message.answer(t(lang, "not_found"))
        return
    await message.answer(
        t(lang, "search_results", query=html.escape(code)),
        reply_markup=movie_list_keyboard(results, lang),
    )


# ---------------------- /start ----------------------

@router.my_chat_member(F.chat.type == "private")
async def on_bot_blocked_or_unblocked(event: ChatMemberUpdated):
    """Foydalanuvchi botni bloklasa/blokdan chiqarsa, holati yangilanadi"""
    status = event.new_chat_member.status
    if status == "kicked":
        await db.set_user_active(event.from_user.id, False)
    elif status == "member":
        await db.set_user_active(event.from_user.id, True)


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    """/start [kod | ref_<id>] — avval obuna tekshiriladi, keyin (kod bo'lsa) kino yuboriladi"""
    user_id = message.from_user.id
    await state.clear()

    args = message.text.split(maxsplit=1)
    code = args[1].strip() if len(args) > 1 else ""

    referrer = None
    if code.startswith("ref_"):
        ref_id = code[4:]
        code = ""
        if ref_id.isdigit() and int(ref_id) != user_id and await db.is_user_exists(int(ref_id)):
            referrer = int(ref_id)

    is_new = await db.add_user(user_id, message.from_user.username, referred_by=referrer)
    if is_new:
        if (message.from_user.language_code or "").startswith("ru"):
            await db.set_lang(user_id, "ru")
        if referrer:
            try:
                count = await db.get_referral_count(referrer)
                ref_lang = await db.get_lang(referrer)
                await bot.send_message(referrer, t(ref_lang, "new_referral", count=count))
            except (TelegramBadRequest, TelegramForbiddenError):
                pass

    lang = await db.get_lang(user_id)
    is_admin = user_id in ADMIN_IDS
    reply_kb = main_keyboard(user_id, lang)

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        if is_admin:
            await message.answer("🔧 Admin panel tugmasi yoqildi.", reply_markup=reply_kb)
        await ask_to_subscribe(message, code, missing, lang)
        return

    if not code:
        await message.answer(welcome_text(message.from_user, lang), reply_markup=reply_kb)
        return

    await handle_movie_code_request(message, bot, code)


# ---------------------- Admin bilan chat ----------------------

@router.message(F.text.in_(all_texts("btn_chat")))
async def start_admin_chat(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    await state.set_state(ChatStates.chatting)
    await message.answer(t(lang, "chat_prompt"), reply_markup=close_chat_keyboard(lang))


@router.message(StateFilter(ChatStates.chatting), F.text.in_(all_texts("btn_close_chat")))
async def close_admin_chat(message: Message, state: FSMContext):
    lang = await db.get_lang(message.from_user.id)
    await state.clear()
    await message.answer(t(lang, "chat_closed"), reply_markup=user_reply_keyboard(lang))


@router.message(StateFilter(ChatStates.chatting))
async def forward_to_admins(message: Message, bot: Bot):
    user = message.from_user
    lang = await db.get_lang(user.id)
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

    await message.answer(t(lang, "chat_sent" if delivered else "chat_failed"))


# ---------------------- Menyu: ommabop, yangi, janrlar, sevimlilar ----------------------

@router.message(F.text.in_(all_texts("btn_popular")))
async def show_popular(message: Message):
    lang = await db.get_lang(message.from_user.id)
    movies = await db.get_popular_movies(10)
    if not movies:
        await message.answer(t(lang, "empty_list"))
        return
    await message.answer(t(lang, "popular_title"), reply_markup=movie_list_keyboard(movies, lang))


@router.message(F.text.in_(all_texts("btn_new")))
async def show_new(message: Message):
    lang = await db.get_lang(message.from_user.id)
    movies = await db.get_newest_movies(10)
    if not movies:
        await message.answer(t(lang, "empty_list"))
        return
    await message.answer(t(lang, "new_title"), reply_markup=movie_list_keyboard(movies, lang))


@router.message(F.text.in_(all_texts("btn_genres")))
async def show_genres(message: Message):
    lang = await db.get_lang(message.from_user.id)
    await message.answer(t(lang, "genres_title"), reply_markup=genres_keyboard())


@router.callback_query(F.data.startswith("genre:"))
async def callback_genre(callback: CallbackQuery):
    _, idx, offset = callback.data.split(":")
    idx, offset = int(idx), int(offset)
    if not 0 <= idx < len(GENRES):
        await callback.answer()
        return
    lang = await db.get_lang(callback.from_user.id)
    genre = GENRES[idx]
    total = await db.get_category_count(genre)
    if total == 0:
        await callback.answer(t(lang, "genre_empty"), show_alert=True)
        return
    movies = await db.get_movies_by_category(genre, offset, PAGE_SIZE)
    await callback.message.edit_text(
        t(lang, "genre_title", genre=genre),
        reply_markup=movie_list_keyboard(movies, lang, f"genre:{idx}", offset, total),
    )
    await callback.answer()


async def favorites_view(user_id: int, offset: int, lang: str):
    total = await db.get_favorites_count(user_id)
    if total == 0:
        return t(lang, "favs_empty"), None
    movies = await db.get_favorites(user_id, offset, PAGE_SIZE)
    return t(lang, "favs_title"), movie_list_keyboard(movies, lang, "favs", offset, total)


@router.message(F.text.in_(all_texts("btn_favs")))
async def show_favorites(message: Message):
    lang = await db.get_lang(message.from_user.id)
    text, keyboard = await favorites_view(message.from_user.id, 0, lang)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("favs:"))
async def callback_favorites_page(callback: CallbackQuery):
    lang = await db.get_lang(callback.from_user.id)
    text, keyboard = await favorites_view(callback.from_user.id, int(callback.data.split(":")[1]), lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ---------------------- Referal ----------------------

@router.message(F.text.in_(all_texts("btn_invite")))
async def show_invite(message: Message):
    user_id = message.from_user.id
    lang = await db.get_lang(user_id)
    count = await db.get_referral_count(user_id)
    top = await db.get_top_referrers(5)
    if top:
        top_text = "\n".join(
            f"{i}. {('@' + username) if username else tg_id} — {c}"
            for i, (tg_id, username, c) in enumerate(top, 1)
        )
    else:
        top_text = t(lang, "invite_empty_top")
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    await message.answer(
        t(lang, "invite", link=link, count=count, top=html.escape(top_text)),
        disable_web_page_preview=True,
    )


# ---------------------- Til ----------------------

@router.message(F.text.in_(all_texts("btn_lang")))
async def show_language_choice(message: Message):
    lang = await db.get_lang(message.from_user.id)
    await message.answer(t(lang, "choose_lang"), reply_markup=lang_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def callback_set_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang not in ("uz", "ru"):
        await callback.answer()
        return
    await db.set_lang(callback.from_user.id, lang)
    await callback.message.delete()
    await callback.message.answer(
        t(lang, "lang_set"), reply_markup=main_keyboard(callback.from_user.id, lang)
    )
    await callback.answer()


# ---------------------- Kino tugmalari: ochish, qism, baho, sevimli ----------------------

@router.callback_query(F.data.startswith("mv:"))
async def callback_open_movie(callback: CallbackQuery, bot: Bot):
    code = callback.data.split(":", maxsplit=1)[1]
    await deliver_movie(callback.message, bot, callback.from_user.id, code)
    await callback.answer()


@router.callback_query(F.data.startswith("part:"))
async def callback_open_part(callback: CallbackQuery, bot: Bot):
    _, code, part = callback.data.rsplit(":", 2)
    await deliver_movie(callback.message, bot, callback.from_user.id, code, int(part))
    await callback.answer()


async def refresh_movie_keyboard(callback: CallbackQuery, code: str, part: int):
    keyboard = await build_movie_kb(callback.from_user.id, code, part)
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("rate:"))
async def callback_rate(callback: CallbackQuery):
    _, code, value, part = callback.data.rsplit(":", 3)
    lang = await db.get_lang(callback.from_user.id)
    await db.toggle_rating(callback.from_user.id, code, int(value))
    await refresh_movie_keyboard(callback, code, int(part))
    await callback.answer(t(lang, "rated"))


@router.callback_query(F.data.startswith("fav:"))
async def callback_favorite(callback: CallbackQuery):
    _, code, part = callback.data.rsplit(":", 2)
    lang = await db.get_lang(callback.from_user.id)
    added = await db.toggle_favorite(callback.from_user.id, code)
    await refresh_movie_keyboard(callback, code, int(part))
    await callback.answer(t(lang, "fav_added" if added else "fav_removed"))


# ---------------------- Kod/nom matni va obunani tekshirish ----------------------

@router.message(F.text, ~F.text.startswith("/"))
async def handle_plain_text_code(message: Message, bot: Bot):
    """Buyruq bo'lmagan har qanday matn kino kodi (yoki nomi) sifatida qaraladi"""
    code = message.text.strip()
    if not code:
        return

    await db.add_user(telegram_id=message.from_user.id, username=message.from_user.username)
    await handle_movie_code_request(message, bot, code)


@router.callback_query(F.data.startswith("check_sub:"))
async def callback_check_subscription(callback: CallbackQuery, bot: Bot):
    """'Obunani tekshirish' tugmasi bosilganda ishlaydi"""
    user_id = callback.from_user.id
    lang = await db.get_lang(user_id)
    code = callback.data.split(":", maxsplit=1)[1]

    missing = await get_unsubscribed_channels(bot, user_id)
    if missing:
        await callback.answer(t(lang, "sub_missing"), show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=subscribe_keyboard(code, missing, lang))
        return

    await callback.message.delete()
    if not code:
        await callback.message.answer(
            welcome_text(callback.from_user, lang), reply_markup=main_keyboard(user_id, lang)
        )
        await callback.answer(t(lang, "sub_ok"))
        return

    sent = await send_movie_part(bot, user_id, code, 1, lang)
    if sent:
        await callback.answer(t(lang, "sub_ok"))
    else:
        await callback.message.answer(t(lang, "not_found"))
        await callback.answer()
