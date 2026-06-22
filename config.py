# config.py — Bot konfiguratsiyasi
# Barcha qiymatlar environment variable'lardan o'qiladi.
# Lokal ishlash uchun ".env" faylidan, serverda (Railway va h.k.) esa
# platforma sozlamalaridan beriladi.

import os

from dotenv import load_dotenv

load_dotenv()  # .env faylidagi qiymatlarni os.environ ga yuklaydi (serverda .env bo'lmasa, shunchaki o'tkazib yuboriladi)


def _get_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable o'rnatilmagan. .env faylini tekshiring.")
    return value


# Bot tokeni (@BotFather dan olinadi)
BOT_TOKEN = _get_required("BOT_TOKEN")

# Bot username (@ belgisisiz), deep link yaratishda ishlatiladi
BOT_USERNAME = _get_required("BOT_USERNAME")

# Admin foydalanuvchilarning Telegram ID lari ro'yxati, vergul bilan ajratilgan
# Masalan: ADMIN_IDS=111111111,222222222
# ID ni bilish uchun @userinfobot ga /start bosing
ADMIN_IDS = [int(x.strip()) for x in _get_required("ADMIN_IDS").split(",") if x.strip()]

# PUBLIC kanal — foydalanuvchilarga ko'rinadigan kanal (reklama/post kanal)
# Obunani tekshirish shu kanal orqali amalga oshiriladi.
PUBLIC_CHANNEL_USERNAME = _get_required("PUBLIC_CHANNEL_USERNAME")  # @ belgisisiz

# PRIVATE guruh — hozircha botda ishlatilmaydi (admin video faylni to'g'ridan-to'g'ri
# botga yuborib qo'shadi), kelajakda zaxira sifatida kerak bo'lishi mumkin
PRIVATE_CHANNEL_ID = int(os.getenv("PRIVATE_CHANNEL_ID", "0")) or None

# SQLite ma'lumotlar bazasi fayli yo'li.
# Railway'da persistent volume mount qilingan papkaga yo'naltirish uchun
# DB_PATH environment variable orqali o'zgartiriladi (masalan: /data/movie_bot.db)
DB_NAME = os.getenv("DB_PATH", "movie_bot.db")
