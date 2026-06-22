# keyboards/user_kb.py — Oddiy foydalanuvchi uchun inline tugmalar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import PUBLIC_CHANNEL_USERNAME


def subscribe_keyboard(movie_code: str) -> InlineKeyboardMarkup:
    """Obuna bo'lmagan foydalanuvchiga ko'rsatiladigan tugma:
    kanalga o'tish va keyin obunani qayta tekshirish.
    movie_code — foydalanuvchi so'ragan kino kodi, obuna tasdiqlangach
    aynan shu kinoni yuborish uchun callback_data ichida saqlanadi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Kanalga obuna bo'lish",
                    url=f"https://t.me/{PUBLIC_CHANNEL_USERNAME}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Obunani tekshirish",
                    callback_data=f"check_sub:{movie_code}",
                )
            ],
        ]
    )
    return keyboard
