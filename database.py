# database.py — SQLite bilan ishlash uchun barcha funksiyalar (aiosqlite asosida)

import aiosqlite
from datetime import datetime

from config import DB_NAME


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

        # So'rovlar jadvali (statistika uchun — har bir kino so'rovi yoziladi)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_code TEXT NOT NULL,
                request_date TEXT NOT NULL
            )
        """)

        await db.commit()


# ---------------------- USERS ----------------------

async def add_user(telegram_id: int, username: str | None):
    """Yangi foydalanuvchini bazaga qo'shadi (agar mavjud bo'lmasa)"""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        existing = await cursor.fetchone()
        if existing is None:
            await db.execute(
                "INSERT INTO users (telegram_id, username, joined_date) VALUES (?, ?, ?)",
                (telegram_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            await db.commit()
            return True  # yangi foydalanuvchi qo'shildi
        return False  # foydalanuvchi allaqachon mavjud


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
    today = datetime.now().strftime("%Y-%m-%d")
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

async def add_movie(code: str, file_id: str, name: str, file_type: str = "video") -> bool:
    """Yangi kino qo'shadi. Kod band bo'lsa False qaytaradi"""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO movies (code, file_id, file_type, name, added_date) VALUES (?, ?, ?, ?, ?)",
                (code, file_id, file_type, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
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


# ---------------------- REQUESTS ----------------------

async def add_request(user_id: int, movie_code: str):
    """Foydalanuvchi kino so'roviga oid yozuv qo'shadi (statistika uchun)"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO requests (user_id, movie_code, request_date) VALUES (?, ?, ?)",
            (user_id, movie_code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()


async def get_today_requests_count() -> int:
    """Bugungi kino so'rovlari sonini qaytaradi"""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM requests WHERE request_date LIKE ?", (f"{today}%",)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
