import threading
import time
import requests
from bs4 import BeautifulSoup
from database import get_word_cache, save_word_cache
from scraper import scrape_longman_ultimate

# ═══════════════════════════════════════════════════════════════
#  AVTO-SCRAPER — Longman saytining o'z so'zlar ro'yxatidan
#  Telegram botdan mustaqil, hech qachon to'xtamaydi
# ═══════════════════════════════════════════════════════════════

SITEMAP_INDEX   = "https://www.ldoceonline.com/sitemap.xml"
DELAY_WORDS     = 8     # So'zlar orasidagi pauza (soniya) — sayt bloklamasligi uchun
DELAY_ON_ERROR  = 30    # Scraping xatosida kutish (soniya)
DELAY_RESTART   = 120   # Butun ro'yxat tugaganda qayta boshlash (soniya)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}


def _fetch_sitemap_urls(url):
    """Berilgan sitemap URL'dan barcha <loc> manzillarini qaytaradi."""
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "lxml-xml")
                return [loc.text.strip() for loc in soup.find_all("loc")]
            print(f"⚠️ Sitemap HTTP {resp.status_code}: {url}")
        except Exception as e:
            print(f"❌ Sitemap yuklanmadi [{attempt}/3]: {e}")
        time.sleep(10)
    return []


def _get_all_word_urls():
    """
    Longman sitemap.xml dan barcha lug'at so'z sahifalarini topadi.
    Sitemap index bo'lsa — har bir kichik sitemapni ham tekshiradi.
    Faqat /dictionary/ yo'lidagi URLlarni qaytaradi.
    """
    print(f"📥 Longman sitemap yuklanmoqda: {SITEMAP_INDEX}")
    all_locs = _fetch_sitemap_urls(SITEMAP_INDEX)

    if not all_locs:
        print("❌ Sitemap bo'sh yoki yuklanmadi.")
        return []

    word_urls = []

    for loc in all_locs:
        if "sitemap" in loc.lower() and loc.endswith(".xml"):
            # Bu kichik sitemap — uning ichidagi URLlarni olish
            sub_locs = _fetch_sitemap_urls(loc)
            for u in sub_locs:
                if "/dictionary/" in u:
                    word_urls.append(u)
        elif "/dictionary/" in loc:
            word_urls.append(loc)

    # Takrorlarni olib tashlash, tartibga keltirish
    word_urls = list(dict.fromkeys(word_urls))
    print(f"✅ {len(word_urls)} ta so'z sahifasi topildi.")
    return word_urls


def _url_to_word(url):
    """
    https://www.ldoceonline.com/dictionary/hello-world
    → "hello-world"  (Longman scraper shu ko'rinishdagi so'zlarni qabul qiladi)
    """
    return url.rstrip("/").split("/dictionary/")[-1]


def _scraper_loop():
    """
    Asosiy sikl — hech qachon to'xtamaydi:
      - Telegram xatosi   → ta'sir qilmaydi (mustaqil thread)
      - Scraping xatosi   → DELAY_ON_ERROR soniya kutib, keyingi so'zga o'tadi
      - Ro'yxat tugasa    → qaytadan boshidan boshlaydi
    """
    print("🚀 Avto-scraper LONGMAN SITEMAP rejimida ishga tushdi!")

    while True:
        word_urls = _get_all_word_urls()

        if not word_urls:
            print(f"⏳ So'z topilmadi. {DELAY_RESTART}s kutib qayta urinadi...")
            time.sleep(DELAY_RESTART)
            continue

        for url in word_urls:
            word = _url_to_word(url)
            if not word or len(word) < 2:
                continue

            # ── Firebase'da borligini tekshir ─────────────────────────
            try:
                existing = get_word_cache(word)
            except Exception as e:
                print(f"⚠️ Firebase tekshiruvda xato ({word}): {e}")
                existing = None

            if existing:
                continue  # Allaqachon bor — keyingisiga

            # ── Longman saytidan yuklab ol (3 marta urinish) ──────────
            success = False
            for attempt in range(1, 4):
                try:
                    data = scrape_longman_ultimate(word)
                    if data:
                        save_word_cache(word, data)
                        print(f"✅ Saqlandi [{attempt}/3]: {word}")
                    else:
                        print(f"⚠️ Topilmadi: {word}")
                    success = True
                    break
                except Exception as e:
                    print(f"❌ Xato [{attempt}/3] ({word}): {e}")
                    if attempt < 3:
                        time.sleep(DELAY_ON_ERROR)

            if not success:
                print(f"🔁 {word} o'tkazib yuborildi.")

            time.sleep(DELAY_WORDS)

        print(f"♻️  Barcha so'zlar ko'rib chiqildi! {DELAY_RESTART}s kutib qayta boshlanadi...")
        time.sleep(DELAY_RESTART)


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════

def start_scraper_thread():
    """
    Scraperiyi Telegram botdan butunlay ajratilgan daemon thread'da ishlatadi.
    """
    t = threading.Thread(target=_scraper_loop, name="ScraperThread", daemon=True)
    t.start()
    print("🧵 ScraperThread ishga tushirildi (Telegram'dan mustaqil).")
    return t


# Eski asyncio versiyasi bilan moslik
async def auto_fill_database():
    start_scraper_thread()
