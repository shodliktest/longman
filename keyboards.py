from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import ADMIN_ID

def get_main_menu(uid):
    kb = ReplyKeyboardBuilder()
    kb.button(text="📜 Tarix")
    kb.button(text="⚙️ Sozlamalar")
    kb.button(text="👨‍💻 Bog'lanish")
    kb.button(text="ℹ️ Yordam")
    if uid == ADMIN_ID: 
        kb.button(text="🔑 Admin Panel")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def get_settings_kb(u_data):
    kb = InlineKeyboardBuilder()
    ex_text = "🚫 Misollarni o'chirish" if u_data.get('show_examples') else "📝 Misollarni yoqish"
    tr_text = "🔤 Tarjimani o'chirish" if u_data.get('show_translation') else "🌐 Tarjimani yoqish"
    kb.button(text=ex_text, callback_data="toggle_examples")
    kb.button(text=tr_text, callback_data="toggle_translation")
    kb.adjust(1)
    return kb.as_markup()

def get_parts_kb(data_keys):
    kb = InlineKeyboardBuilder()
    for pos in data_keys:
        kb.button(text=pos, callback_data=f"v_{pos}")
    if len(data_keys) > 1:
        kb.button(text="📚 Barchasi (All)", callback_data="v_all")
    kb.adjust(2)
    return kb.as_markup()

def get_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data="adm_stats")
    kb.button(text="📋 Userlar Ro'yxati", callback_data="adm_list_menu")
    kb.button(text="📢 Broadcast", callback_data="adm_bc")
    kb.button(text="📁 So'zlar Ro'yxatini Yuklash", callback_data="adm_upload_words")
    kb.adjust(1)
    return kb.as_markup()

def get_list_format_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Chatda ko'rish", callback_data="list_chat")
    kb.button(text="📁 TXT faylida olish", callback_data="list_txt")
    kb.adjust(2)
    return kb.as_markup()

def get_contact_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Adminga xabar yozish", callback_data="msg_to_admin")
    return kb.as_markup()
