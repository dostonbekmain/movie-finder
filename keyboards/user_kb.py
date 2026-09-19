# keyboards/user_kb.py — Oddiy foydalanuvchi uchun inline tugmalar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def subscribe_keyboard(movie_code: str, channels) -> InlineKeyboardMarkup:
    """Obuna bo'linmagan kanallar tugmalari + obunani qayta tekshirish tugmasi.
    channels — (id, chat_id, title, link) ro'yxati.
    movie_code — obuna tasdiqlangach yuboriladigan kino kodi (bo'sh bo'lishi mumkin)"""
    rows = [
        [InlineKeyboardButton(text=f"📢 {title}", url=link)]
        for _, _, title, link in channels
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="✅ Obunani tekshirish",
                callback_data=f"check_sub:{movie_code}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
