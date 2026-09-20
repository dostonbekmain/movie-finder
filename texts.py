# texts.py — foydalanuvchi uchun matnlar (o'zbek va rus tillarida)

DEFAULT_LANG = "uz"

TEXTS = {
    "uz": {
        "welcome": "👋 Salom, {name}! Kino kodini yoki nomini yuboring, yoki quyidagi menyudan foydalaning.",
        "subscribe": "📢 Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
        "check_sub": "✅ Obunani tekshirish",
        "sub_missing": "❌ Siz hali barcha kanallarga obuna bo'lmagansiz!",
        "sub_ok": "✅ Obuna tasdiqlandi!",
        "not_found": "❌ Bunday kino topilmadi.",
        "copyright": (
            "⚠️ Mualliflik huquqi sababli bu kino {minutes} daqiqadan keyin o'chiriladi. "
            "Iltimos, uni hoziroq «Saqlangan xabarlar» (Saved Messages) ga yoki qurilmangizga saqlab oling."
        ),
        "search_results": "🔎 «{query}» bo'yicha topilgan kinolar:",
        "btn_popular": "🔥 Ommabop",
        "btn_new": "🆕 Yangi",
        "btn_genres": "🎭 Janrlar",
        "btn_favs": "⭐ Sevimlilarim",
        "btn_invite": "👥 Taklif qilish",
        "btn_lang": "🌐 Til",
        "btn_chat": "💬 Admin bilan chat",
        "btn_close_chat": "❌ Chatni yopish",
        "popular_title": "🔥 Eng ko'p ko'rilgan kinolar:",
        "new_title": "🆕 Yangi qo'shilgan kinolar:",
        "genres_title": "🎭 Janrni tanlang:",
        "genre_title": "🎭 {genre} kinolari:",
        "genre_empty": "Bu janrda hozircha kino yo'q.",
        "favs_title": "⭐ Sevimli kinolaringiz:",
        "favs_empty": "Sevimlilar ro'yxati bo'sh. Kino ostidagi «⭐» tugmasi bilan qo'shing.",
        "empty_list": "Hozircha kinolar yo'q.",
        "fav_added": "⭐ Sevimlilarga qo'shildi",
        "fav_removed": "Sevimlilardan olib tashlandi",
        "rated": "Bahoyingiz qabul qilindi",
        "choose_lang": "🌐 Tilni tanlang:",
        "lang_set": "✅ Til o'zgartirildi.",
        "invite": (
            "👥 Do'stlaringizni taklif qiling!\n\n"
            "🔗 Sizning havolangiz:\n{link}\n\n"
            "✅ Siz taklif qilganlar: {count}\n\n"
            "🏆 TOP taklif qiluvchilar:\n{top}"
        ),
        "invite_empty_top": "Hozircha hech kim yo'q.",
        "new_referral": "🎉 Sizning havolangiz orqali yangi foydalanuvchi qo'shildi! Jami: {count}",
        "chat_prompt": (
            "💬 Xabaringizni yozing, u adminga yuboriladi. Admin javobi shu yerga keladi.\n"
            "Chiqish uchun «❌ Chatni yopish» ni bosing."
        ),
        "chat_closed": "✅ Chat yopildi.",
        "chat_sent": "✅ Adminga yuborildi.",
        "chat_failed": "❌ Xabarni yuborib bo'lmadi.",
        "admin_reply": "💬 Admin javobi:",
        "prev": "⬅️ Oldingi",
        "next": "Keyingi ➡️",
    },
    "ru": {
        "welcome": "👋 Привет, {name}! Отправьте код или название фильма, либо воспользуйтесь меню ниже.",
        "subscribe": "📢 Чтобы пользоваться ботом, сначала подпишитесь на каналы:",
        "check_sub": "✅ Проверить подписку",
        "sub_missing": "❌ Вы ещё не подписались на все каналы!",
        "sub_ok": "✅ Подписка подтверждена!",
        "not_found": "❌ Такой фильм не найден.",
        "copyright": (
            "⚠️ Из-за авторских прав этот фильм будет удалён через {minutes} мин. "
            "Пожалуйста, сохраните его сейчас в «Избранное» (Saved Messages) или на устройство."
        ),
        "search_results": "🔎 Найденные фильмы по запросу «{query}»:",
        "btn_popular": "🔥 Популярные",
        "btn_new": "🆕 Новинки",
        "btn_genres": "🎭 Жанры",
        "btn_favs": "⭐ Избранное",
        "btn_invite": "👥 Пригласить",
        "btn_lang": "🌐 Язык",
        "btn_chat": "💬 Чат с админом",
        "btn_close_chat": "❌ Закрыть чат",
        "popular_title": "🔥 Самые просматриваемые фильмы:",
        "new_title": "🆕 Недавно добавленные фильмы:",
        "genres_title": "🎭 Выберите жанр:",
        "genre_title": "🎭 Фильмы жанра {genre}:",
        "genre_empty": "В этом жанре пока нет фильмов.",
        "favs_title": "⭐ Ваши избранные фильмы:",
        "favs_empty": "Список избранного пуст. Добавляйте кнопкой «⭐» под фильмом.",
        "empty_list": "Фильмов пока нет.",
        "fav_added": "⭐ Добавлено в избранное",
        "fav_removed": "Удалено из избранного",
        "rated": "Ваша оценка принята",
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык изменён.",
        "invite": (
            "👥 Приглашайте друзей!\n\n"
            "🔗 Ваша ссылка:\n{link}\n\n"
            "✅ Вы пригласили: {count}\n\n"
            "🏆 ТОП приглашающих:\n{top}"
        ),
        "invite_empty_top": "Пока никого нет.",
        "new_referral": "🎉 По вашей ссылке зашёл новый пользователь! Всего: {count}",
        "chat_prompt": (
            "💬 Напишите сообщение, оно будет отправлено админу. Ответ придёт сюда.\n"
            "Для выхода нажмите «❌ Закрыть чат»."
        ),
        "chat_closed": "✅ Чат закрыт.",
        "chat_sent": "✅ Отправлено админу.",
        "chat_failed": "❌ Не удалось отправить сообщение.",
        "admin_reply": "💬 Ответ админа:",
        "prev": "⬅️ Назад",
        "next": "Далее ➡️",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS[DEFAULT_LANG])[key]
    return text.format(**kwargs) if kwargs else text


def all_texts(key: str) -> set[str]:
    """Bir kalitning barcha tillardagi matnlari (tugma matnini filtrlash uchun)"""
    return {texts[key] for texts in TEXTS.values()}
