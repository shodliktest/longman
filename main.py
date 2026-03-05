import streamlit as st
import threading
import asyncio
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Longman AI Dashboard", page_icon="📕", layout="wide")

from bot_handlers import dp, bot
from database import (
    get_all_users, get_stats, increment_page_view,
    get_daily_word_stats, get_daily_user_stats, get_word_list_info
)
from auto_scraper import start_scraper_thread, set_bot, upload_word_list
from config import ADMIN_ID

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #00ffcc; }
    div[data-testid="stMetric"] { background-color: #1c1f26; border: 2px solid #00ffcc; border-radius: 10px; padding: 15px; text-align: center;}
    div[data-testid="stMetricLabel"] { color: #ff00ff !important; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

if 'visited' not in st.session_state:
    st.session_state.visited = True
    increment_page_view()

try:
    stats        = get_stats()
    word_stats   = get_daily_word_stats()
    user_stats   = get_daily_user_stats()
    latest_users = get_all_users(limit_count=50)
    word_list_info = get_word_list_info()

    total_words       = sum([w['count'] for w in word_stats]) if word_stats else 0
    total_users_count = stats.get('total_users', 0)
    if total_users_count == 0 and latest_users:
        total_users_count = len(latest_users)

    st.title("📕 Longman Ultimate Pro - Boshqaruv Paneli")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Foydalanuvchilar", f"{total_users_count} ta")
    c2.metric("📚 Bazadagi So'zlar", f"{total_words} ta")
    c3.metric("🔍 Jami Qidiruvlar", f"{stats.get('total_searches', 0)} ta")
    c4.metric("👁 Saytga Tashriflar", f"{stats.get('page_views', 0)} marta")

    st.markdown("### 📈 Rivojlanish Dinamikasi")

    df_users_graph = pd.DataFrame(user_stats)
    if not df_users_graph.empty and 'date' in df_users_graph.columns:
        df_users_graph['date'] = pd.to_datetime(df_users_graph['date']).dt.date
        df_users_graph.rename(columns={'count': 'Soni'}, inplace=True)
        df_users_graph['Tur'] = 'Yangi Userlar'
    else:
        df_users_graph = pd.DataFrame(columns=['date', 'Soni', 'Tur'])

    df_words = pd.DataFrame(word_stats)
    if not df_words.empty and 'date' in df_words.columns:
        df_words['date'] = pd.to_datetime(df_words['date']).dt.date
        df_words.rename(columns={'count': 'Soni'}, inplace=True)
        df_words['Tur'] = "Yangi So'zlar"
    else:
        df_words = pd.DataFrame(columns=['date', 'Soni', 'Tur'])

    df_combined = pd.concat([df_users_graph, df_words])
    if not df_combined.empty:
        fig = px.line(df_combined, x='date', y='Soni', color='Tur', markers=True, template="plotly_dark")
        fig.update_traces(line_width=3, marker=dict(size=8))
        fig.update_layout(legend_title_text="Ko'rsatkichlar", hovermode="x unified")
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("📊 Hozircha grafik chizish uchun yetarli ma'lumot yo'q.")

    st.markdown(f"### 📋 Oxirgi Qo'shilgan {len(latest_users)} ta Foydalanuvchi")
    df_display = pd.DataFrame(latest_users)
    show_cols = ['name', 'username', 'id', 'joined_at', 'search_count', 'last_active']
    if not df_display.empty:
        for c in show_cols:
            if c not in df_display.columns: df_display[c] = "-"
        df_display = df_display[show_cols].copy()
        df_display.columns = ["Ism", "Username", "ID", "Qo'shilgan vaqti", "Qidiruvlari", "Oxirgi faollik"]
        st.dataframe(df_display, width='stretch', hide_index=True)
    else:
        st.write("Hozircha foydalanuvchilar yo'q.")

    # ══════════════════════════════════════════════════
    # 📁 SO'ZLAR RO'YXATINI YUKLASH BO'LIMI
    # ══════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📁 So'zlar Ro'yxatini Boshqarish")

    col_info, col_upload = st.columns([1, 2])

    with col_info:
        st.markdown("#### 📊 Joriy Holat")
        st.metric("📋 Ro'yxatdagi so'zlar", f"{word_list_info['count']} ta")
        st.caption(f"🕐 Oxirgi yangilanish: {word_list_info['updated_at']}")

        if word_list_info['count'] > 0:
            scraper_threads = [t for t in threading.enumerate() if t.name == "ScraperThread"]
            if scraper_threads:
                st.success("🟢 Scraper ishlayapti")
            else:
                st.warning("🟡 Scraper to'xtagan")

            # Namuna so'zlar
            sample = word_list_info['words'][:20]
            if sample:
                st.caption("Namuna: " + ", ".join(sample))
        else:
            st.info("📭 Ro'yxat bo'sh. TXT fayl yuklang.")

    with col_upload:
        st.markdown("#### ⬆️ Yangi Ro'yxat Yuklash")
        st.caption("📌 Format: `hello, call, low, world` (vergul bilan) yoki har qatorda bitta so'z")

        uploaded_file = st.file_uploader(
            "TXT fayl tanlang",
            type=["txt"],
            help="Vergul bilan ajratilgan yoki har qatorda bitta so'z bo'lgan TXT fayl"
        )

        manual_text = st.text_area(
            "Yoki so'zlarni qo'lda kiriting:",
            placeholder="hello, call, low, world, ...",
            height=100
        )

        if st.button("🚀 Ro'yxatni Yuklash va Scraperga Yuborish", type="primary"):
            text_to_upload = ""

            if uploaded_file is not None:
                text_to_upload = uploaded_file.read().decode("utf-8")
            elif manual_text.strip():
                text_to_upload = manual_text.strip()
            else:
                st.error("❌ Fayl yoki matn kiriting!")
                st.stop()

            with st.spinner("⏳ Saqlanmoqda..."):
                count, words = upload_word_list(text_to_upload)

            if count == 0:
                st.error("❌ Ro'yxat bo'sh yoki noto'g'ri format!")
            else:
                preview = ", ".join(words[:15])
                if len(words) > 15:
                    preview += f" ... va yana {len(words)-15} ta"
                st.success(f"✅ **{count} ta so'z** saqlandi! Scraper avtomatik boshlanadi.")
                st.caption(f"Namuna: {preview}")
                st.rerun()

except Exception as e:
    st.warning(f"Xatolik yuz berdi: {e}")


# --- BOTNI ORQA FONDA ISHGA TUSHIRISH ---
def run_bot_in_background():
    async def _runner():
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, handle_signals=False)
        except Exception as e:
            print(f"Polling xatosi: {e}")

    def _t():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_runner())

    if not any(t.name == "BotThread" for t in threading.enumerate()):
        threading.Thread(target=_t, name="BotThread", daemon=True).start()

run_bot_in_background()

# Bot instance'ni scraperga uzatish (admin xabarlari uchun)
set_bot(bot, ADMIN_ID)

# --- AVTO-SCRAPERNI ISHGA TUSHIRISH ---
start_scraper_thread()
