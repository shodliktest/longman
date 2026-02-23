import asyncio
from database import get_word_cache, save_word_cache
from scraper import scrape_longman_ultimate

# --- ENG KO'P ISHLATILADIGAN SO'ZLAR RO'YXATI ---
# Bu yerga internetdan Top 3000 ta so'zni topib, ro'yxatni to'ldirib qo'yasiz.
# Hozircha namuna sifatida bir nechta so'z yozilgan:
TOP_WORDS = [
    "abandon", "ability", "able", "about", "above", "abroad", "absence", 
    "absolute", "absolutely", "absorb", "abuse", "academic", "accept", 
    "access", "accident", "accompany", "accomplish", "according", "account"
    # Shu yerga qolgan minglab so'zlarni vergul bilan ajratib yozib chiqasiz...
]

async def auto_fill_database():
    """Orqa fonda har 30 soniyada bitta so'zni bazaga saqlaydigan funksiya"""
    
    # Bot to'liq ishga tushib olishi va server o'ziga kelishi uchun 10 soniya kutamiz
    await asyncio.sleep(10)
    print("🔄 Avto-scraper ishga tushdi! Bazani to'ldirish boshlandi...")
    
    for word in TOP_WORDS:
        word = word.lower().strip()
        
        # 1. Avval bazada bor-yo'qligini tekshiramiz
        existing_data = get_word_cache(word)
        
        if not existing_data:
            # 2. Agar bazada yo'q bo'lsa, saytdan tortamiz
            try:
                data = await asyncio.to_thread(scrape_longman_ultimate, word)
                if data:
                    save_word_cache(word, data)
                    print(f"✅ Avto-saqlandi: {word}")
                else:
                    print(f"⚠️ Topilmadi: {word}")
            except Exception as e:
                print(f"❌ Xatolik ({word}): {e}")
            
            # 3. Saytni bloklamasligi uchun qat'iy 30 soniya tanaffus!
            await asyncio.sleep(30) 
        else:
            # Agar so'z allaqachon bazada bo'lsa, uni kutib o'tirmaymiz.
            # Tezlik uchun 0.1s pauza qilib, keyingi so'zga o'tib ketamiz.
            await asyncio.sleep(0.1)
