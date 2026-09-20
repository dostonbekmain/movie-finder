# keyboards/user_kb.py — Oddiy foydalanuvchi uchun tugmalar

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import GENRES
from texts import t

PAGE_SIZE = 10


def user_reply_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [t(lang, "btn_popular"), t(lang, "btn_new")],
        [t(lang, "btn_genres"), t(lang, "btn_favs")],
        [t(lang, "btn_invite"), t(lang, "btn_lang")],
        [t(lang, "btn_chat")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text) for text in row] for row in rows],
        resize_keyboard=True,
    )


def close_chat_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_close_chat"))]], resize_keyboard=True
    )


def subscribe_keyboard(movie_code: str, channels, lang: str) -> InlineKeyboardMarkup:
    """Obuna bo'linmagan kanallar tugmalari + obunani qayta tekshirish tugmasi.
    channels — (id, chat_id, title, link) ro'yxati"""
    rows = [
        [InlineKeyboardButton(text=f"📢 {title}", url=link)]
        for _, _, title, link in channels
    ]
    rows.append(
        [InlineKeyboardButton(text=t(lang, "check_sub"), callback_data=f"check_sub:{movie_code}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def movie_keyboard(
    code: str, part: int, parts: int, likes: int, dislikes: int, is_fav: bool
) -> InlineKeyboardMarkup:
    """Kino ostidagi tugmalar: qismlar (serial bo'lsa), baho va sevimlilar"""
    rows = []
    if parts > 1:
        buttons = [
            InlineKeyboardButton(
                text=f"• {n} •" if n == part else str(n), callback_data=f"part:{code}:{n}"
            )
            for n in range(1, parts + 1)
        ]
        for i in range(0, len(buttons), 5):
            rows.append(buttons[i : i + 5])
    rows.append(
        [
            InlineKeyboardButton(text=f"👍 {likes}", callback_data=f"rate:{code}:1:{part}"),
            InlineKeyboardButton(text=f"👎 {dislikes}", callback_data=f"rate:{code}:-1:{part}"),
            InlineKeyboardButton(
                text="⭐✔️" if is_fav else "⭐", callback_data=f"fav:{code}:{part}"
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def movie_list_keyboard(
    movies, lang: str, prefix: str | None = None, offset: int = 0, total: int = 0
) -> InlineKeyboardMarkup:
    """Kinolar ro'yxati (har biri alohida tugma). prefix berilsa — sahifalash tugmalari ham chiqadi"""
    rows = [
        [InlineKeyboardButton(text=f"🎬 {name}"[:60], callback_data=f"mv:{code}")]
        for code, name in movies
    ]
    if prefix:
        nav = []
        if offset > 0:
            nav.append(
                InlineKeyboardButton(
                    text=t(lang, "prev"), callback_data=f"{prefix}:{max(offset - PAGE_SIZE, 0)}"
                )
            )
        if offset + PAGE_SIZE < total:
            nav.append(
                InlineKeyboardButton(
                    text=t(lang, "next"), callback_data=f"{prefix}:{offset + PAGE_SIZE}"
                )
            )
        if nav:
            rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def genres_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(GENRES), 2):
        rows.append(
            [
                InlineKeyboardButton(text=GENRES[j], callback_data=f"genre:{j}:0")
                for j in range(i, min(i + 2, len(GENRES)))
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ]
        ]
    )
