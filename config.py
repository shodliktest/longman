import streamlit as st

try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
    ADMIN_ID = int(st.secrets["ADMIN_ID"])
except Exception as e:
    st.error(f"❌ Secrets bo'limida xatolik (BOT_TOKEN yoki ADMIN_ID yo'q): {e}")
    st.stop()
