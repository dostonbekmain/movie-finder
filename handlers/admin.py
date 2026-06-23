# handlers/admin.py — Admin panel handlerlari
# Statistika, kino qo'shish/o'chirish, ro'yxatlar, broadcast

import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

import database as db
from config import ADMIN_IDS, BOT_USERNAME, DB_NAME
from keyboards.admin_kb import (
    admin_main_menu,
    pagination_keyboard,
    back_to_admin_menu,
    ADMIN_PANEL_BUTTON_TEXT,
)

router = Router()

PAGE_LIMIT = 10


# ---------------------- FSM holatlari ----------------------

class AddMovieStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_name = State()
    waiting_for_code = State()


class BroadcastStates(StatesGroup):
    waiting_for_text = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------------------- /admin asosiy menyu ----------------------

@router.message(Command("admin"))
@router.message(F.text == ADMIN_PANEL_BUTTON_TEXT)
async def cmd_admin(message: Message):
    """Faqat ADMIN_IDS dagi foydalanuvchilar uchun admin panelni ochadi.
    /admin buyrug'i bilan yoki doimiy "🔧 Admin panel" tugmasi bilan chaqiriladi"""
    if message.from_user.id not in ADMIN_IDS:
        return  # admin bo'lmasa — e'tibor berilmaydi

    await message.answer("🔧 Admin panel:", reply_markup=admin_main_menu())


@router.callback_query(F.data == "admin_back")
async def callback_admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await callback.message.edit_text("🔧 Admin panel:", reply_markup=admin_main_menu())


# ---------------------- 1. Statistika ----------------------

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    movies_count = await db.get_movies_count()
    users_count = await db.get_users_count()
    today_new_users = await db.get_today_new_users_count()
    today_requests = await db.get_today_requests_count()

    text = (
        "📊 Statistika:\n\n"
        f"🎬 Jami kinolar: {movies_count}\n"
        f"👥 Jami foydalanuvchilar: {users_count}\n"
        f"🆕 Bugungi yangi foydalanuvchilar: {today_new_users}\n"
        f"📥 Bugungi kino so'rovlari: {today_requests}"
    )
    await callback.message.edit_text(text, reply_markup=back_to_admin_menu())
    await callback.answer()


# ---------------------- 2. Kino qo'shish ----------------------

@router.callback_query(F.data == "admin_add_movie")
async def callback_admin_add_movie(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AddMovieStates.waiting_for_video)
    await callback.message.edit_text("🎬 Kinoni (video faylni) yuboring.")
    await callback.answer()


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    """Alternativ usul: /add buyrug'i orqali kino qo'shishni boshlash"""
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AddMovieStates.waiting_for_video)
    await message.answer("🎬 Kinoni (video faylni) yuboring.")


@router.message(StateFilter(AddMovieStates.waiting_for_video), F.video)
async def process_movie_video(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(file_id=message.video.file_id, file_type="video")
    await state.set_state(AddMovieStates.waiting_for_name)
    await message.answer("✍️ Endi kino nomini yuboring (masalan: Avengers: Endgame).")


@router.message(StateFilter(AddMovieStates.waiting_for_video), F.document)
async def process_movie_document(message: Message, state: FSMContext):
    """Ba'zi formatlar (masalan .mkv) Telegramda video sifatida emas,
    document sifatida keladi — buni ham qabul qilamiz"""
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.update_data(file_id=message.document.file_id, file_type="document")
    await state.set_state(AddMovieStates.waiting_for_name)
    await message.answer("✍️ Endi kino nomini yuboring (masalan: Avengers: Endgame).")


@router.message(StateFilter(AddMovieStates.waiting_for_video))
async def process_movie_video_invalid(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("❌ Iltimos, video yoki fayl (document) ko'rinishida yuboring.")


@router.message(StateFilter(AddMovieStates.waiting_for_name))
async def process_movie_name(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("❌ Iltimos, kino nomini matn ko'rinishida yuboring.")
        return

    await state.update_data(name=name)
    await state.set_state(AddMovieStates.waiting_for_code)
    await message.answer("✍️ Endi kino kodini yuboring (masalan: 1234).")


@router.message(StateFilter(AddMovieStates.waiting_for_code))
async def process_movie_code(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    code = message.text.strip() if message.text else ""
    if not code:
        await message.answer("❌ Iltimos, kino kodini matn ko'rinishida yuboring.")
        return

    data = await state.get_data()
    file_id = data.get("file_id")
    file_type = data.get("file_type", "video")
    name = data.get("name", code)

    added = await db.add_movie(code=code, file_id=file_id, name=name, file_type=file_type)
    await state.clear()

    if not added:
        await message.answer(f"❌ '{code}' kodi allaqachon band. Boshqa kod tanlang.")
        return

    deep_link = f"https://t.me/{BOT_USERNAME}?start={code}"
    await message.answer(
        f"✅ Kino qo'shildi!\n\nNomi: {name}\nKod: {code}\nDeep link: {deep_link}\n\n"
        "Ushbu havolani PUBLIC kanaldagi post tugmasiga biriktiring."
    )


# ---------------------- 3. Kino o'chirish ----------------------

@router.callback_query(F.data == "admin_delete_movie")
async def callback_admin_delete_movie(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.edit_text(
        "🗑 Kinoni o'chirish uchun quyidagi buyruqni yuboring:\n\n"
        "/delete <kod>\n\nMasalan: /delete 1234",
        reply_markup=back_to_admin_menu(),
    )
    await callback.answer()


@router.message(Command("delete"))
async def cmd_delete(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("❗ Foydalanish: /delete <kod>")
        return

    code = args[1].strip()
    deleted = await db.delete_movie(code)
    if deleted:
        await message.answer(f"✅ '{code}' kodli kino o'chirildi.")
    else:
        await message.answer(f"❌ '{code}' kodli kino topilmadi.")


@router.message(Command("rename"))
async def cmd_rename(message: Message):
    """Mavjud kinoning nomini o'zgartiradi: /rename <kod> <yangi nom>"""
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3 or not args[2].strip():
        await message.answer("❗ Foydalanish: /rename <kod> <yangi nom>\nMasalan: /rename 1 Avengers: Endgame")
        return

    code, new_name = args[1].strip(), args[2].strip()
    updated = await db.update_movie_name(code, new_name)
    if updated:
        await message.answer(f"✅ '{code}' kodli kino nomi '{new_name}' ga o'zgartirildi.")
    else:
        await message.answer(f"❌ '{code}' kodli kino topilmadi.")


# ---------------------- 4. Kinolar ro'yxati ----------------------

@router.callback_query(F.data.startswith("admin_movies_list:"))
async def callback_admin_movies_list(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    offset = int(callback.data.split(":")[1])
    movies = await db.get_all_movies(offset=offset, limit=PAGE_LIMIT)
    total = await db.get_movies_count()

    if not movies:
        text = "📋 Kinolar ro'yxati bo'sh."
    else:
        lines = [f"{code} — {name}" for code, name in movies]
        text = "📋 Kinolar ro'yxati:\n\n" + "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=pagination_keyboard("admin_movies_list", offset, PAGE_LIMIT, total),
    )
    await callback.answer()


# ---------------------- 5. Foydalanuvchilar ----------------------

@router.callback_query(F.data.startswith("admin_users_list:"))
async def callback_admin_users_list(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    offset = int(callback.data.split(":")[1])
    users = await db.get_all_users(offset=offset, limit=PAGE_LIMIT)
    total = await db.get_users_count()

    if not users:
        text = "👥 Foydalanuvchilar ro'yxati bo'sh."
    else:
        lines = [
            f"ID: {tg_id} | @{username or '—'} | {joined_date}"
            for tg_id, username, joined_date in users
        ]
        text = "👥 Foydalanuvchilar ro'yxati:\n\n" + "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=pagination_keyboard("admin_users_list", offset, PAGE_LIMIT, total),
    )
    await callback.answer()


# ---------------------- 6. Broadcast ----------------------

@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.edit_text(
        "📢 Barchaga xabar yuborish uchun quyidagi buyruqni ishlating:\n\n"
        "/broadcast <matn>",
        reply_markup=back_to_admin_menu(),
    )
    await callback.answer()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("❗ Foydalanish: /broadcast <matn>")
        return

    text = args[1].strip()
    user_ids = await db.get_all_user_ids()

    sent_count = 0
    failed_count = 0
    for telegram_id in user_ids:
        try:
            await bot.send_message(chat_id=telegram_id, text=text)
            sent_count += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed_count += 1
        await asyncio.sleep(0.05)  # Telegram limitlariga tushib qolmaslik uchun

    await message.answer(
        f"✅ Broadcast yakunlandi.\nYuborildi: {sent_count}\nXatolik: {failed_count}"
    )


# ---------------------- 7. Baza zaxirasi (backup) ----------------------

@router.message(Command("backup"))
async def cmd_backup(message: Message, bot: Bot):
    """Joriy SQLite bazasini (movie_bot.db) document sifatida adminga yuboradi.
    Serverdagi (masalan Railway) bazani lokal nusxalash/tekshirish uchun foydali"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await bot.send_document(
        chat_id=message.from_user.id,
        document=FSInputFile(DB_NAME),
        caption="🗄 Bazaning joriy nusxasi",
    )
