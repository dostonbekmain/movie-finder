# reports.py — statistika grafigi va kunlik hisobot matnlari

import html

import database as db


def _bar(value: int, max_value: int, width: int = 10) -> str:
    if max_value <= 0 or value <= 0:
        return ""
    return "█" * max(1, round(value / max_value * width))


async def weekly_chart() -> str:
    """Oxirgi 7 kun uchun matnli grafik (yangi foydalanuvchilar va kino so'rovlari)"""
    rows = await db.get_daily_counts(7)
    max_users = max(r[1] for r in rows)
    max_requests = max(r[2] for r in rows)

    lines = ["👤 Yangi foydalanuvchilar:"]
    lines += [f"{d[5:]} {_bar(u, max_users):<10} {u}" for d, u, _ in rows]
    lines += ["", "📥 Kino so'rovlari:"]
    lines += [f"{d[5:]} {_bar(r, max_requests):<10} {r}" for d, _, r in rows]
    return "📈 Oxirgi 7 kun\n<pre>" + html.escape("\n".join(lines), quote=False) + "</pre>"


async def daily_report() -> str:
    movies = await db.get_movies_count()
    users = await db.get_users_count()
    left = await db.get_left_users_count()
    today_users = await db.get_today_new_users_count()
    today_requests = await db.get_today_requests_count()
    top = await db.get_popular_movies(3)

    top_text = "\n".join(f"{i}. {html.escape(name)} ({code})" for i, (code, name) in enumerate(top, 1))
    return (
        "🗓 Kunlik hisobot\n\n"
        f"🎬 Kinolar: {movies}\n"
        f"👥 Foydalanuvchilar: {users} (tark etganlar: {left})\n"
        f"🆕 Bugungi yangi foydalanuvchilar: {today_users}\n"
        f"📥 Bugungi so'rovlar: {today_requests}\n\n"
        + (f"🔥 TOP kinolar:\n{top_text}\n\n" if top else "")
        + await weekly_chart()
    )
