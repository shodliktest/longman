import threading
import time
from database import get_word_cache, save_word_cache, get_word_list, save_word_list
from scraper import scrape_longman_ultimate

# ═══════════════════════════════════════════════════════════════
#  AVTO-SCRAPER — Admin yuklagan TXT fayldagi so'zlarni saqlaydi
#  Threading asosida, hech qachon to'xtamaydi
# ═══════════════════════════════════════════════════════════════

DELAY_WORDS    = 5    # So'zlar orasidagi pauza (soniya)
DELAY_ERROR    = 30   # Xato bo'lganda kutish (soniya)
DELAY_NO_LIST  = 60   # Ro'yxat yo'q bo'lganda tekshirish oralig'i (soniya)

_bot_instance  = None
_admin_id      = None


def set_bot(bot, admin_id):
    """main.py dan bot va admin_id ni uzatish uchun."""
    global _bot_instance, _admin_id
    _bot_instance = bot
    _admin_id     = admin_id


def _notify_admin(text):
    """Adminga Telegram xabari yuboradi (sinxron)."""
    if not _bot_instance or not _admin_id:
        return
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_bot_instance.send_message(_admin_id, text, parse_mode="HTML"))
        loop.close()
    except Exception as e:
        print(f"⚠️ Admin xabari yuborilmadi: {e}")


def parse_word_list(text):
    """
    TXT fayl tarkibini parse qiladi.
    Formatlar: vergul bilan (hello, call, low) yoki yangi qator
    """
    import re
    words = re.split(r'[,\n\r]+', text)
    result = []
    for w in words:
        w = w.strip().lower()
        if len(w) >= 2:
            result.append(w)
    seen = set()
    unique = []
    for w in result:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def upload_word_list(text):
    """Admin yuklagan TXT matnini parse qilib Firebase'ga saqlaydi."""
    words = parse_word_list(text)
    if words:
        save_word_list(words)
        print(f"📋 Yangi ro'yxat saqlandi: {len(words)} ta so'z")
    return len(words), words


def _scraper_loop():
    print("🚀 Avto-scraper ishga tushdi! Admin ro'yxati rejimi faollashdi.")

    while True:
        words = get_word_list()

        if not words:
            print(f"⏳ So'zlar ro'yxati yo'q. {DELAY_NO_LIST}s kutib qayta tekshiradi...")
            time.sleep(DELAY_NO_LIST)
            continue

        print(f"📋 Ro'yxatdan {len(words)} ta so'z topildi. Scraping boshlanadi...")
        _notify_admin(
            f"🚀 <b>Avto-scraper boshlandi!</b>\n"
            f"📋 Ro'yxatda: <b>{len(words)} ta so'z</b>\n"
            f"⏱ Taxminiy vaqt: ~{len(words) * DELAY_WORDS // 60} daqiqa"
        )

        saved   = 0
        skipped = 0
        errors  = 0

        for i, word in enumerate(words):
            try:
                existing = get_word_cache(word)
            except Exception as e:
                print(f"⚠️ Firebase tekshiruvda xato ({word}): {e}")
                existing = None

            if existing:
                skipped += 1
                continue

            success = False
            for attempt in range(1, 4):
                try:
                    data = scrape_longman_ultimate(word)
                    if data:
                        save_word_cache(word, data)
                        saved += 1
                        print(f"✅ [{i+1}/{len(words)}] Saqlandi: {word}")
                    else:
                        print(f"⚠️ [{i+1}/{len(words)}] Topilmadi: {word}")
                    success = True
                    break
                except Exception as e:
                    print(f"❌ Xato [{attempt}/3] ({word}): {e}")
                    if attempt < 3:
                        time.sleep(DELAY_ERROR)

            if not success:
                errors += 1
                print(f"🔁 O'tkazib yuborildi: {word}")

            time.sleep(DELAY_WORDS)

        done_msg = (
            f"✅ <b>Scraping yakunlandi!</b>\n\n"
            f"📊 Natijalar:\n"
            f"  ✅ Saqlandi: <b>{saved} ta</b>\n"
            f"  ⏭ Allaqachon bor edi: <b>{skipped} ta</b>\n"
            f"  ❌ Xato: <b>{errors} ta</b>\n\n"
            f"📋 Yangi ro'yxat yuklash uchun admin paneldan foydalaning."
        )
        print(f"♻️ Ro'yxat tugadi! saved={saved}, skipped={skipped}, errors={errors}")
        _notify_admin(done_msg)
        save_word_list([])
        print(f"⏳ Yangi ro'yxat kutilmoqda...")
        time.sleep(DELAY_NO_LIST)


def start_scraper_thread():
    if any(t.name == "ScraperThread" for t in threading.enumerate()):
        print("ℹ️  ScraperThread allaqachon ishlamoqda.")
        return None
    t = threading.Thread(target=_scraper_loop, name="ScraperThread", daemon=True)
    t.start()
    print("🧵 ScraperThread ishga tushirildi.")
    return t


async def auto_fill_database():
    start_scraper_thread()
