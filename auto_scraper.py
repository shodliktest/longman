"""
auto_scraper.py

Ma'lumotlar oqimi:
  Admin TXT yuklaydi (Telegram yoki Web)
        ↓
  ram_store.set_words()  ← RAM ga saqlanadi (rerun ta'sir qilmaydi)
        ↓
  ScraperThread har bir so'zni Longman.com dan scrape qiladi
        ↓
  Firebase: word_cache/{word} = { ta'rif, misollar, audio... }
        ↓
  So'z ro'yxati tugagach RAM tozalanadi (ta'riflar Firebaseda qoladi)
"""

import threading
import time
import re

import ram_store
from database import get_word_cache, save_word_cache, get_word_list, save_word_list
from scraper import scrape_longman_ultimate

DELAY_WORDS   = 5
DELAY_ERROR   = 30
DELAY_NO_LIST = 60

_bot_instance = None
_admin_id     = None


def set_bot(bot, admin_id):
    global _bot_instance, _admin_id
    _bot_instance = bot
    _admin_id     = admin_id


def _notify_admin(text: str):
    if not _bot_instance or not _admin_id:
        return
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            _bot_instance.send_message(_admin_id, text, parse_mode="HTML")
        )
        loop.close()
    except Exception as e:
        print(f"[Scraper] ⚠️ Admin xabari yuborilmadi: {e}")


def parse_word_list(text: str) -> list:
    parts = re.split(r'[,\n\r]+', text)
    seen, result = set(), []
    for w in parts:
        w = w.strip().lower()
        if len(w) >= 2 and w not in seen:
            seen.add(w)
            result.append(w)
    return result


def upload_word_list(text: str, source: str = "web"):
    """
    RAM ga saqlaydi + Firebase ga zaxira.
    Streamlit rerun, sahifa yopish, brauzer o'zgarmaydi — RAM saqlanib qoladi.
    """
    words = parse_word_list(text)
    if words:
        ram_store.set_words(words, source=source)
        save_word_list(words)
    return len(words), words


def ram_get_info() -> dict:
    return ram_store.get_info()


def ram_clear_word_list():
    ram_store.clear()
    save_word_list([])


def _scraper_loop():
    print("[Scraper] 🚀 Ishga tushdi. Admin ro'yxatini kutmoqda...")

    while True:
        if not ram_store.has_words():
            fb_words = get_word_list()
            if fb_words:
                print(f"[Scraper] 🔄 Firebase dan {len(fb_words)} ta so'z tiklandi.")
                ram_store.set_words(fb_words, source="firebase-restore")
            else:
                print(f"[Scraper] ⏳ Ro'yxat yo'q. {DELAY_NO_LIST}s kutilmoqda...")
                time.sleep(DELAY_NO_LIST)
                continue

        info = ram_store.get_info()
        print(f"[Scraper] 📋 {info['remaining']} ta so'z qoldi (jami {info['total']}). Boshlanmoqda...")
        _notify_admin(
            f"🚀 <b>Avto-scraper boshlandi!</b>\n"
            f"📋 Jami: <b>{info['total']} ta so'z</b>\n"
            f"⏳ Qolgan: <b>{info['remaining']} ta</b>\n"
            f"⏱ Taxminiy: ~{info['remaining'] * DELAY_WORDS // 60} daqiqa"
        )

        saved = skipped = errors = 0

        while ram_store.has_words():
            word = ram_store.pop_word()
            if not word:
                break

            try:
                existing = get_word_cache(word)
            except Exception as e:
                print(f"[Scraper] ⚠️ Firebase xato ({word}): {e}")
                existing = None

            if existing:
                skipped += 1
                print(f"[Scraper] ⏭ Mavjud: {word}")
                continue

            success = False
            for attempt in range(1, 4):
                try:
                    data = scrape_longman_ultimate(word)
                    if data:
                        save_word_cache(word, data)
                        saved += 1
                        cur = ram_store.get_info()
                        print(f"[Scraper] ✅ {word} | qoldi: {cur['remaining']}/{cur['total']}")
                    else:
                        print(f"[Scraper] ⚠️ Topilmadi: {word}")
                    success = True
                    break
                except Exception as e:
                    print(f"[Scraper] ❌ [{attempt}/3] {word}: {e}")
                    if attempt < 3:
                        time.sleep(DELAY_ERROR)

            if not success:
                errors += 1

            time.sleep(DELAY_WORDS)

        _notify_admin(
            f"✅ <b>Scraping yakunlandi!</b>\n\n"
            f"  ✅ Saqlandi: <b>{saved} ta</b>\n"
            f"  ⏭ Allaqachon bor edi: <b>{skipped} ta</b>\n"
            f"  ❌ Xato: <b>{errors} ta</b>\n\n"
            f"📋 Yangi ro'yxat yuklash uchun admin paneldan foydalaning."
        )
        print(f"[Scraper] ♻️ Tugadi. saved={saved}, skipped={skipped}, errors={errors}")

        ram_store.clear()
        save_word_list([])
        time.sleep(DELAY_NO_LIST)


def start_scraper_thread():
    if any(t.name == "ScraperThread" for t in threading.enumerate()):
        print("[Scraper] ℹ️ ScraperThread allaqachon ishlamoqda.")
        return None
    t = threading.Thread(target=_scraper_loop, name="ScraperThread", daemon=True)
    t.start()
    print("[Scraper] 🧵 ScraperThread ishga tushirildi.")
    return t


async def auto_fill_database():
    start_scraper_thread()
