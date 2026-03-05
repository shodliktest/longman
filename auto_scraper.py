import threading
import time
import requests
from database import get_word_cache, save_word_cache
from scraper import scrape_longman_ultimate

# ═══════════════════════════════════════════════════════════════
#  AVTO-SCRAPER — 20,000 ta eng ko'p ishlatiladigan ingliz so'zi
#  Threading asosida, hech qachon to'xtamaydi
# ═══════════════════════════════════════════════════════════════

WORDS_URL     = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/20k.txt"
DELAY_WORDS   = 5    # So'zlar orasidagi pauza (soniya) — sayt bloklamasligi uchun
DELAY_ERROR   = 30   # Xato bo'lganda kutish (soniya)
DELAY_RESTART = 300  # Ro'yxat tugagandan keyin qayta boshlash (soniya)


def _fetch_word_list():
    """GitHub'dan 20,000 ta so'zni streaming usulda yuklaydi (RAM tejovchi)."""
    print(f"📥 So'zlar ro'yxati yuklanmoqda: {WORDS_URL}")
    for attempt in range(1, 4):
        try:
            response = requests.get(WORDS_URL, stream=True, timeout=15)
            if response.status_code == 200:
                words = []
                for line in response.iter_lines():
                    if line:
                        word = line.decode('utf-8').strip().lower()
                        if len(word) >= 2:
                            words.append(word)
                print(f"✅ {len(words)} ta so'z yuklandi.")
                return words
            else:
                print(f"⚠️ HTTP {response.status_code} — ro'yxat yuklanmadi.")
        except Exception as e:
            print(f"❌ Yuklash xatosi [{attempt}/3]: {e}")
        time.sleep(10)
    return []


def _scraper_loop():
    """
    Asosiy sikl — hech qachon to'xtamaydi:
      - Network xatosi    → DELAY_ERROR soniya kutib, keyingi so'zga o'tadi
      - Scraping xatosi   → xuddi shunday
      - Ro'yxat tugasa    → DELAY_RESTART soniya kutib, qaytadan boshidan
      - Streamlit restart → daemon thread bo'lgani uchun ta'sir qilmaydi
    """
    print("🚀 Avto-scraper ishga tushdi! 20k so'zlar rejimi faollashdi.")

    while True:
        words = _fetch_word_list()

        if not words:
            print(f"⏳ Ro'yxat yuklanmadi. {DELAY_RESTART}s kutib qayta urinadi...")
            time.sleep(DELAY_RESTART)
            continue

        skipped = 0
        saved   = 0
        errors  = 0

        for word in words:
            # ── Firebase'da borligini tekshir ────────────────────────
            try:
                existing = get_word_cache(word)
            except Exception as e:
                print(f"⚠️ Firebase tekshiruvda xato ({word}): {e}")
                existing = None

            if existing:
                skipped += 1
                continue  # Allaqachon bor — keyingisiga (pauza yo'q, tez o'tadi)

            # ── Longman saytidan yuklab ol ────────────────────────────
            success = False
            for attempt in range(1, 4):
                try:
                    data = scrape_longman_ultimate(word)
                    if data:
                        save_word_cache(word, data)
                        print(f"✅ Saqlandi: {word}  (skip={skipped}, saved={saved+1})")
                        saved += 1
                    else:
                        print(f"⚠️ Topilmadi: {word}")
                    success = True
                    break
                except Exception as e:
                    print(f"❌ Xato [{attempt}/3] ({word}): {e}")
                    if attempt < 3:
                        time.sleep(DELAY_ERROR)

            if not success:
                errors += 1
                print(f"🔁 O'tkazib yuborildi: {word}  (errors={errors})")

            time.sleep(DELAY_WORDS)

        print(
            f"♻️  20k ro'yxat tugadi! "
            f"saqlandi={saved}, o'tkazildi(bor edi)={skipped}, xato={errors}. "
            f"{DELAY_RESTART}s kutib qayta boshlanadi..."
        )
        time.sleep(DELAY_RESTART)


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════

def start_scraper_thread():
    """
    Scraperiyi Telegram bot va Streamlit'dan butunlay ajratilgan
    daemon thread'da ishlatadi. Streamlit qayta yuklansa ham to'xtamaydi.
    """
    if any(t.name == "ScraperThread" for t in threading.enumerate()):
        print("ℹ️  ScraperThread allaqachon ishlamoqda.")
        return None

    t = threading.Thread(target=_scraper_loop, name="ScraperThread", daemon=True)
    t.start()
    print("🧵 ScraperThread ishga tushirildi (Telegram va Streamlit'dan mustaqil).")
    return t


# Eski asyncio versiyasi bilan moslik (main.py o'zgartirmaslik uchun)
async def auto_fill_database():
    start_scraper_thread()
