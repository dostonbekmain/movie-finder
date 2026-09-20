# database.py — SQLite bilan ishlash uchun barcha funksiyalar (aiosqlite asosida)

import aiosqlite
from datetime import datetime, timedelta, timezone

from config import DB_NAME

UZ_TZ = timezone(timedelta(hours=5))


def now() -> datetime:
    """O'zbekiston vaqti (server qaysi mintaqada bo'lishidan qat'i nazar)"""
    return datetime.now(UZ_TZ)


async def init_db():
    """Bot ishga tushganda jadvallarni yaratish (agar mavjud bo'lmasa)"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Kinolar jadvali
        # file_type — 'video' yoki 'document' (masalan .mkv fayllar Telegramda
        # document sifatida keladi), yuborishda shu turga mos usul ishlatiladi
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL DEFAULT 'video',
                name TEXT NOT NULL,
                added_date TEXT NOT NULL
            )
        """)

        # Eski bazalarda file_type ustuni bo'lmasligi mumkin — mavjud bo'lmasa qo'shamiz
        cursor = await db.execute("PRAGMA table_info(movies)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "file_type" not in columns:
            await db.execute(
                "ALTER TABLE movies ADD COLUMN file_type TEXT NOT NULL DEFAULT 'video'"
            )

        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                joined_date TEXT NOT NULL
            )
        """)

        # is_active: 0 — foydalanuvchi botni bloklagan/tark etgan
        cursor = await db.execute("PRAGMA table_info(users)")
        user_columns = [row[1] for row in await cursor.fetchall()]
        if "is_active" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        if "referred_by" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        if "lang" not in user_columns:
            await db.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'uz'")

        if "category" not in columns:
            await db.execute("ALTER TABLE movies ADD COLUMN category TEXT")

        # Serial qismlari (1-qism — movies jadvalidagi asosiy fayl, 2+ shu yerda)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                ep_no INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL DEFAULT 'video',
                UNIQUE (code, ep_no)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                value INTEGER NOT NULL,
                PRIMARY KEY (user_id, code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                added_date TEXT NOT NULL,
                PRIMARY KEY (user_id, code)
            )
        """)

        # So'rovlar jadvali (statistika uchun — har bir kino so'rovi yoziladi)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_code TEXT NOT NULL,
                request_date TEXT NOT NULL
            )
        """)

        # Majburiy obuna kanallari
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                added_date TEXT NOT NULL
            )
        """)

        # Sozlamalar (kalit-qiymat)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Admin bilan chat: adminga yuborilgan xabar -> qaysi foydalanuvchidan ekani
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_map (
                admin_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (admin_id, message_id)
            )
        """)

        await db.commit()


# ---------------------- ADMIN CHAT ----------------------

async def save_chat_link(admin_id: int, message_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chat_map (admin_id, message_id, user_id) VALUES (?, ?, ?)",
            (admin_id, message_id, user_id),
        )
        await db.commit()


async def get_chat_user(admin_id: int, message_id: int) -> int | None:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT user_id FROM chat_map WHERE admin_id = ? AND message_id = ?",
            (admin_id, message_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


# ---------------------- SETTINGS ----------------------

DEFAULT_DELETE_MINUTES = 3


async def get_delete_minutes() -> int:
    """Kino xabari necha daqiqadan keyin o'chiriladi (0 — o'chirilmaydi)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'delete_minutes'")
        row = await cursor.fetchone()
        return int(row[0]) if row else DEFAULT_DELETE_MINUTES


async def set_delete_minutes(minutes: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('delete_minutes', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(minutes),),
        )
        await db.commit()


# ---------------------- CHANNELS ----------------------

async def add_channel(chat_id: int, title: str, link: str) -> bool:
    """Majburiy kanal qo'shadi. Allaqachon mavjud bo'lsa False qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO channels (chat_id, title, link, added_date) VALUES (?, ?, ?, ?)",
                (chat_id, title, link, now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_channels():
    """Barcha majburiy kanallar: (id, chat_id, title, link)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, chat_id, title, link FROM channels ORDER BY id")
        return await cursor.fetchall()


async def delete_channel(channel_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()
        return cursor.rowcount > 0


# ---------------------- USERS ----------------------

async def add_user(telegram_id: int, username: str | None, referred_by: int | None = None):
    """Yangi foydalanuvchini bazaga qo'shadi (agar mavjud bo'lmasa)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        existing = await cursor.fetchone()
        if existing is None:
            await db.execute(
                "INSERT INTO users (telegram_id, username, joined_date, referred_by) VALUES (?, ?, ?, ?)",
                (telegram_id, username, now().strftime("%Y-%m-%d %H:%M:%S"), referred_by),
            )
            await db.commit()
            return True  # yangi foydalanuvchi qo'shildi
        await db.execute("UPDATE users SET is_active = 1 WHERE telegram_id = ?", (telegram_id,))
        await db.commit()
        return False  # foydalanuvchi allaqachon mavjud


async def set_user_active(telegram_id: int, active: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET is_active = ? WHERE telegram_id = ?",
            (1 if active else 0, telegram_id),
        )
        await db.commit()


async def get_left_users_count() -> int:
    """Botni bloklagan/tark etgan foydalanuvchilar soni"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_active = 0")
        result = await cursor.fetchone()
        return result[0] if result else 0


async def is_user_exists(telegram_id: int) -> bool:
    """Foydalanuvchi bazada bor-yo'qligini tekshiradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        result = await cursor.fetchone()
        return result is not None


async def get_users_count() -> int:
    """Jami foydalanuvchilar sonini qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        result = await cursor.fetchone()
        return result[0] if result else 0


async def get_today_new_users_count() -> int:
    """Bugun qo'shilgan yangi foydalanuvchilar sonini qaytaradi"""
    today = now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE joined_date LIKE ?", (f"{today}%",)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0


async def get_all_users(offset: int = 0, limit: int = 10):
    """Foydalanuvchilar ro'yxatini sahifalab qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT telegram_id, username, joined_date FROM users "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()


async def get_all_user_ids() -> list[int]:
    """Broadcast uchun barcha foydalanuvchilarning telegram_id larini qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


# ---------------------- MOVIES ----------------------

async def add_movie(
    code: str, file_id: str, name: str, file_type: str = "video", category: str | None = None
) -> bool:
    """Yangi kino qo'shadi. Kod band bo'lsa False qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO movies (code, file_id, file_type, name, added_date, category) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (code, file_id, file_type, name, now().strftime("%Y-%m-%d %H:%M:%S"), category),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Bu kod allaqachon mavjud
            return False


async def get_movie_by_code(code: str):
    """Kod orqali kinoni topadi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, file_id, file_type, name FROM movies WHERE code = ?", (code,)
        )
        return await cursor.fetchone()


async def delete_movie(code: str) -> bool:
    """Kod orqali kinoni o'chiradi. Topilmasa False qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id FROM movies WHERE code = ?", (code,))
        existing = await cursor.fetchone()
        if existing is None:
            return False
        await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.execute("DELETE FROM episodes WHERE code = ?", (code,))
        await db.execute("DELETE FROM ratings WHERE code = ?", (code,))
        await db.execute("DELETE FROM favorites WHERE code = ?", (code,))
        await db.commit()
        return True


async def update_movie_name(code: str, name: str) -> bool:
    """Kod orqali kinoning nomini o'zgartiradi. Topilmasa False qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id FROM movies WHERE code = ?", (code,))
        existing = await cursor.fetchone()
        if existing is None:
            return False
        await db.execute("UPDATE movies SET name = ? WHERE code = ?", (name, code))
        await db.commit()
        return True


async def get_movies_count() -> int:
    """Jami kinolar sonini qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM movies")
        result = await cursor.fetchone()
        return result[0] if result else 0


async def get_all_movies(offset: int = 0, limit: int = 10):
    """Kinolar ro'yxatini sahifalab qaytaradi (kod + nomi)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, name FROM movies ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_movies(query: str, limit: int = 10):
    """Nom bo'yicha qidirish: [(code, name)]"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, name FROM movies WHERE name LIKE ? ESCAPE '\\' ORDER BY id DESC LIMIT ?",
            (f"%{_like_escape(query)}%", limit),
        )
        return await cursor.fetchall()


async def get_newest_movies(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, name FROM movies ORDER BY id DESC LIMIT ?", (limit,)
        )
        return await cursor.fetchall()


async def get_popular_movies(limit: int = 10):
    """Eng ko'p so'ralgan kinolar: [(code, name)]"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT m.code, m.name FROM requests r JOIN movies m ON m.code = r.movie_code "
            "GROUP BY m.code ORDER BY COUNT(*) DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_movies_by_category(category: str, offset: int = 0, limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT code, name FROM movies WHERE category = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (category, limit, offset),
        )
        return await cursor.fetchall()


async def get_category_count(category: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM movies WHERE category = ?", (category,))
        return (await cursor.fetchone())[0]


# ---------------------- EPISODES (serial qismlari) ----------------------

async def get_parts_count(code: str) -> int:
    """Jami qismlar soni (1-qism har doim bor)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM episodes WHERE code = ?", (code,))
        return 1 + (await cursor.fetchone())[0]


async def add_episode(code: str, file_id: str, file_type: str) -> int:
    """Kinoga keyingi qismni qo'shadi va uning tartib raqamini qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT COALESCE(MAX(ep_no), 1) FROM episodes WHERE code = ?", (code,))
        ep_no = (await cursor.fetchone())[0] + 1
        await db.execute(
            "INSERT INTO episodes (code, ep_no, file_id, file_type) VALUES (?, ?, ?, ?)",
            (code, ep_no, file_id, file_type),
        )
        await db.commit()
        return ep_no


async def get_episode(code: str, ep_no: int):
    """(file_id, file_type) — 2+ qismlar uchun"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT file_id, file_type FROM episodes WHERE code = ? AND ep_no = ?", (code, ep_no)
        )
        return await cursor.fetchone()


# ---------------------- RATINGS & FAVORITES ----------------------

async def toggle_rating(user_id: int, code: str, value: int):
    """Xuddi shu baho qayta bosilsa — bekor qilinadi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT value FROM ratings WHERE user_id = ? AND code = ?", (user_id, code)
        )
        row = await cursor.fetchone()
        if row and row[0] == value:
            await db.execute("DELETE FROM ratings WHERE user_id = ? AND code = ?", (user_id, code))
        else:
            await db.execute(
                "INSERT OR REPLACE INTO ratings (user_id, code, value) VALUES (?, ?, ?)",
                (user_id, code, value),
            )
        await db.commit()


async def get_rating_counts(code: str) -> tuple[int, int]:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(value = 1), 0), COALESCE(SUM(value = -1), 0) "
            "FROM ratings WHERE code = ?",
            (code,),
        )
        likes, dislikes = await cursor.fetchone()
        return likes, dislikes


async def toggle_favorite(user_id: int, code: str) -> bool:
    """Sevimlilarga qo'shadi/olib tashlaydi. Qo'shilgan bo'lsa True qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND code = ?", (user_id, code)
        )
        if await cursor.fetchone():
            await db.execute("DELETE FROM favorites WHERE user_id = ? AND code = ?", (user_id, code))
            await db.commit()
            return False
        await db.execute(
            "INSERT INTO favorites (user_id, code, added_date) VALUES (?, ?, ?)",
            (user_id, code, now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()
        return True


async def is_favorite(user_id: int, code: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND code = ?", (user_id, code)
        )
        return await cursor.fetchone() is not None


async def get_favorites(user_id: int, offset: int = 0, limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT m.code, m.name FROM favorites f JOIN movies m ON m.code = f.code "
            "WHERE f.user_id = ? ORDER BY f.added_date DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset),
        )
        return await cursor.fetchall()


async def get_favorites_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM favorites f JOIN movies m ON m.code = f.code WHERE f.user_id = ?",
            (user_id,),
        )
        return (await cursor.fetchone())[0]


# ---------------------- USER EXTRAS (til, referal, hisobot) ----------------------

async def get_lang(telegram_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT lang FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else "uz"


async def set_lang(telegram_id: int, lang: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET lang = ? WHERE telegram_id = ?", (lang, telegram_id))
        await db.commit()


async def get_referral_count(telegram_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (telegram_id,)
        )
        return (await cursor.fetchone())[0]


async def get_top_referrers(limit: int = 5):
    """[(telegram_id, username, count)]"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT u.telegram_id, u.username, COUNT(*) AS c FROM users r "
            "JOIN users u ON u.telegram_id = r.referred_by "
            "GROUP BY u.telegram_id ORDER BY c DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_active_user_ids() -> list[int]:
    """Reklama yuborish uchun botni bloklamagan foydalanuvchilar"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT telegram_id FROM users WHERE is_active = 1")
        return [row[0] for row in await cursor.fetchall()]


async def get_daily_counts(days: int = 7):
    """Oxirgi `days` kun uchun [(sana, yangi_userlar, so'rovlar)], eskidan yangiga"""
    dates = [(now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    async with aiosqlite.connect(DB_NAME) as db:
        result = []
        for date in dates:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM users WHERE joined_date LIKE ?", (f"{date}%",)
            )
            users = (await cursor.fetchone())[0]
            cursor = await db.execute(
                "SELECT COUNT(*) FROM requests WHERE request_date LIKE ?", (f"{date}%",)
            )
            requests = (await cursor.fetchone())[0]
            result.append((date, users, requests))
        return result


# ---------------------- REQUESTS ----------------------

async def add_request(user_id: int, movie_code: str):
    """Foydalanuvchi kino so'roviga oid yozuv qo'shadi (statistika uchun)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO requests (user_id, movie_code, request_date) VALUES (?, ?, ?)",
            (user_id, movie_code, now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()


async def get_today_requests_count() -> int:
    """Bugungi kino so'rovlari sonini qaytaradi"""
    today = now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM requests WHERE request_date LIKE ?", (f"{today}%",)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
