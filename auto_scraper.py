import asyncio
import requests
from database import get_word_cache, save_word_cache
from scraper import scrape_longman_ultimate

async def auto_fill_database():
    """Orqa fonda har 30 soniyada bitta so'zni bazaga saqlaydi (RAM ni tejovchi Streaming usuli)"""
    
    # Bot ishlab ketishi uchun 10 soniya pauza
    await asyncio.sleep(10)
    print("🔄 Avto-scraper ishga tushdi! Eng tejamkor RAM rejimi faollashdi...")

    # Internetdagi 20,000 ta eng ko'p ishlatiladigan so'zlar bazasi
    # (Buni kelajakda istalgan milliontalik ro'yxat ssilkasi bilan almashtirishingiz mumkin)
    url = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/20k.txt"
    
    try:
        # stream=True buyrug'i faylni to'liq RAMga yuklamaslikka buyruq beradi!
        with requests.get(url, stream=True, timeout=10) as response:
            if response.status_code == 200:
                
                # iter_lines() - ro'yxatni faqat bitta qatordan o'qiydi va oldingisini o'chirib ketadi
                for line in response.iter_lines():
                    if line:
                        word = line.decode('utf-8').strip().lower()
                        
                        # Agar so'z juda qisqa bo'lsa (masalan a, b harflari) o'tkazib yuboramiz
                        if len(word) < 2: continue
                        
                        # 1. Avval Firebase'da bor-yo'qligini tekshiramiz
                        existing_data = get_word_cache(word)
                        
                        if not existing_data:
                            # 2. Bazada yo'q bo'lsa, saytdan tortamiz
                            try:
                                data = await asyncio.to_thread(scrape_longman_ultimate, word)
                                if data:
                                    save_word_cache(word, data)
                                    print(f"✅ Avto-saqlandi: {word}")
                                else:
                                    print(f"⚠️ Topilmadi: {word}")
                            except Exception as e:
                                print(f"❌ Xatolik ({word}): {e}")
                            
                            # 3. Sayt bloklamasligi uchun 30 soniya tanaffus
                            await asyncio.sleep(30)
                        else:
                            # So'z bazada bor. RAM darhol tozalanib, keyingisiga o'tadi
                            await asyncio.sleep(0.01)
                            
    except Exception as e:
        print(f"❌ Internetdan so'zlarni olishda xatolik: {e}")
