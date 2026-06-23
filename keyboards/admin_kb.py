# keyboards/admin_kb.py — Admin panel uchun inline tugmalar

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

ADMIN_PANEL_BUTTON_TEXT = "🔧 Admin panel"


def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """Admin /start bosganda pastda doimiy chiqib turadigan tugma.
    Bosilganda /admin buyrug'i bilan bir xil natija beradi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=ADMIN_PANEL_BUTTON_TEXT)]],
        resize_keyboard=True,
    )


def admin_main_menu() -> InlineKeyboardMarkup:
    """/admin buyrug'i bosilganda chiqadigan asosiy menyu"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data="admin_add_movie")],
            [InlineKeyboardButton(text="📋 Kinolar ro'yxati", callback_data="admin_movies_list:0")],
            [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users_list:0")],
            [InlineKeyboardButton(text="🗄 Backup", callback_data="admin_backup")],
        ]
    )


def pagination_keyboard(prefix: str, offset: int, limit: int, total: int) -> InlineKeyboardMarkup:
    """Ro'yxatlar (kinolar/foydalanuvchilar) uchun oldinga/orqaga sahifalash tugmalari.
    prefix — callback_data prefiksi, masalan 'admin_movies_list' yoki 'admin_users_list'"""
    buttons = []
    row = []
    if offset > 0:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi", callback_data=f"{prefix}:{max(offset - limit, 0)}"
            )
        )
    if offset + limit < total:
        row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️", callback_data=f"{prefix}:{offset + limit}"
            )
        )
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_admin_menu() -> InlineKeyboardMarkup:
    """Oddiy 'Orqaga' tugmasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
    )
