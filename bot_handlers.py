import asyncio
import os
import re
import streamlit as st
from auto_scraper import start_scraper_thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_ID
from database import (
    update_user_activity, get_user_data, save_user_data, increment_search_count,
    get_all_users, get_stats, get_uz_time, save_word_cache, get_word_cache
)
from scraper import scrape_longman_ultimate, format_output
from keyboards import (
    get_main_menu, get_settings_kb, get_parts_kb, 
    get_admin_kb, get_list_format_kb, get_contact_kb
)
from messages import get_welcome_msg, HELP_MSG, get_new_user_admin_msg

try:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
except Exception as e:
    st.error(f"Botni ishga tushirishda xatolik: {e}")
    st.stop()

# Vaqtinchalik xotira
TEMP_CACHE = {}

# MAX 10 TA QIDIRUV (SEMAPHORE)
scrape_semaphore = None

async def get_semaphore():
    global scrape_semaphore
    if scrape_semaphore is None:
        # Bir vaqtning o'zida maksimal 10 kishiga saytdan ma'lumot olishga ruxsat beradi
        scrape_semaphore = asyncio.Semaphore(10)
    return scrape_semaphore

class UserStates(StatesGroup):
    waiting_for_contact_msg = State()

class AdminStates(StatesGroup):
    waiting_for_bc = State()

async def send_sequential_messages(message, text):
    limit = 4000
    if len(text) <= limit: 
        await message.answer(text, parse_mode="HTML")
    else:
        while len(text) > 0:
            split_at = text.rfind('\n', 0, limit) if len(text) > limit else len(text)
            if split_at == -1: split_at = limit
            await message.answer(text[:split_at], parse_mode="HTML")
            text = text[split_at:].strip()

def clean_html(text):
    return text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")

# ==========================================
# --- 1. START VA ASOSIY MENYULAR ---
# ==========================================
@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    is_new = update_user_activity(m.from_user)
    if is_new:
        try:
            u_link = f"@{m.from_user.username}" if m.from_user.username else "Mavjud emas"
            msg = get_new_user_admin_msg(m.from_user.full_name, m.from_user.id, u_link, get_uz_time())
            await bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
        except: pass
    await m.answer(get_welcome_msg(m.from_user.first_name), reply_markup=get_main_menu(m.from_user.id), parse_mode="HTML")

@dp.message(F.text == "ℹ️ Yordam")
async def help_handler(m: types.Message):
    await m.answer(HELP_MSG, parse_mode="HTML")

@dp.message(F.text == "📜 Tarix")
async def btn_history(m: types.Message):
    u_data = get_user_data(m.from_user.id)
    if not u_data.get('history'): 
        return await m.answer("📭 Tarix bo'sh. Hali hech qanday so'z qidirmagansiz.")
    msg = "📜 <b>Oxirgi qidiruvlar:</b>\n\n"
    for i, word in enumerate(u_data['history'], 1): 
        msg += f"{i}. <code>{word}</code>\n"
    await m.answer(msg, parse_mode="HTML")

@dp.message(F.text == "⚙️ Sozlamalar")
async def btn_settings(m: types.Message):
    u_data = get_user_data(m.from_user.id)
    await m.answer("⚙️ <b>Sozlamalar:</b>\n\nQuyidagi tugmalar orqali funksiyalarni yoqing yoki o'chiring:", reply_markup=get_settings_kb(u_data), parse_mode="HTML")

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_settings(call: types.CallbackQuery):
    u_data = get_user_data(call.from_user.id)
    if call.data == "toggle_examples": u_data['show_examples'] = not u_data['show_examples']
    elif call.data == "toggle_translation": u_data['show_translation'] = not u_data['show_translation']
    save_user_data(call.from_user.id, u_data)
    await call.message.edit_reply_markup(reply_markup=get_settings_kb(u_data))
    await call.answer("✅ Sozlama o'zgardi!")

# ==========================================
# --- 2. FOYDALANUVCHI VA ADMIN ALOQASI ---
# ==========================================
@dp.message(F.text == "👨‍💻 Bog'lanish")
async def contact_h(m: types.Message):
    await m.answer("👨‍💻 Admin bilan bog'lanish uchun quyidagi tugmani bosing:", reply_markup=get_contact_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "msg_to_admin")
async def feedback_init(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_contact_msg)
    await call.message.answer("📝 <b>Xabaringizni yozing:</b>", parse_mode="HTML")
    await call.answer()

@dp.message(UserStates.waiting_for_contact_msg)
async def feedback_done(m: types.Message, state: FSMContext):
    await state.clear()
    admin_msg = f"📩 <b>MUROJAAT:</b>\n👤 Kimdan: {m.from_user.full_name}\n🆔 <b>ID:</b> <code>{m.from_user.id}</code>\n📝 Xabar:\n{m.text}"
    try:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
        await m.answer("✅ <b>Xabaringiz adminga yetkazildi!</b>", parse_mode="HTML")
    except: await m.answer("❌ Xatolik yuz berdi.")

@dp.message(F.chat.id == ADMIN_ID, F.reply_to_message)
async def admin_reply_to_user(m: types.Message):
    orig_text = m.reply_to_message.text
    if not orig_text: return
    match = re.search(r"ID:\s*(\d+)", orig_text)
    if match:
        target_id = int(match.group(1))
        try:
            await bot.send_message(target_id, f"👨‍💻 <b>Admin javobi:</b>\n\n{m.text}", parse_mode="HTML")
            await m.answer("✅ Javob yuborildi.")
        except Exception as e: await m.answer(f"❌ Xatolik: ({e})")

# ==========================================
# --- 3. ADMIN PANEL (TEPADA BO'LISHI SHART) ---
# ==========================================
@dp.message(F.text == "🔑 Admin Panel", F.chat.id == ADMIN_ID)
async def admin_main(m: types.Message):
    await m.answer("🛠 <b>Admin Boshqaruv Paneli</b>", reply_markup=get_admin_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "adm_stats")
async def stats_cb(call: types.CallbackQuery):
    s = get_stats()
    users = len(get_all_users())
    msg = (
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Foydalanuvchilar: {users} ta\n"
        f"🔍 Jami qidiruvlar: {s.get('total_searches', 0)} ta\n"
        f"👁 Saytga tashriflar: {s.get('page_views', 0)} marta"
    )
    await call.message.answer(msg, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "adm_list_menu")
async def list_menu_cb(call: types.CallbackQuery):
    await call.message.edit_text("📋 <b>Ro'yxat formatini tanlang:</b>", reply_markup=get_list_format_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("list_"))
async def generate_user_list(call: types.CallbackQuery):
    format_type = call.data.replace("list_", "")
    users = get_all_users()
    await call.message.delete()
    
    if not users: return await call.message.answer("❌ Foydalanuvchilar yo'q.")

    msg_parts = []
    for i, u in enumerate(users, 1):
        name = u.get('name', 'Nomsiz')
        uid = u.get('id', 'Noma\'lum')
        s_count = u.get('search_count', 0)
        joined = u.get('joined_at', 'Noma\'lum')
        msg_parts.append(f"<b>{i}. {name}</b> (ID: <code>{uid}</code>)\n   📅 Qo'shilgan: {joined}\n   🔍 Qidiruvlar: {s_count} ta\n")
        
    full_text = f"📋 <b>FOYDALANUVCHILAR ({len(users)} ta):</b>\n\n" + "\n".join(msg_parts)

    if format_type == "txt":
        file_name = "user_list.txt"
        with open(file_name, "w", encoding="utf-8") as f: f.write(clean_html(full_text))
        await call.message.answer_document(types.FSInputFile(file_name))
        os.remove(file_name)
    else:
        await send_sequential_messages(call.message, full_text)

@dp.callback_query(F.data == "adm_bc")
async def bc_cb(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📢 <b>Broadcast:</b> Hammaga yuboriladigan xabarni yuboring:")
    await state.set_state(AdminStates.waiting_for_bc)
    await call.answer()

@dp.message(AdminStates.waiting_for_bc)
async def bc_process(m: types.Message, state: FSMContext):
    await state.clear()
    users = get_all_users()
    c = 0
    prog = await m.answer(f"⏳ Tarqatish boshlandi... (0/{len(users)})")
    
    for u in users:
        uid = u.get('id')
        if uid:
            try:
                await bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=m.message_id)
                c += 1
                if c % 20 == 0: await prog.edit_text(f"⏳ Tarqatilmoqda... ({c}/{len(users)})")
                await asyncio.sleep(0.05)
            except: pass
    await prog.edit_text(f"✅ Xabar {c} ta foydalanuvchiga yetkazildi.")

# ==========================================
# --- 4. LUG'AT QIDIRISH (ENG PASTDA BO'LISHI SHART) ---
# ==========================================
@dp.message(F.text)
async def handle_word(m: types.Message):
    # Agar foydalanuvchi adashib boshqa menyu tugmasini bossa, qidirib yurmaydi
    if m.text in ["📜 Tarix", "⚙️ Sozlamalar", "👨‍💻 Bog'lanish", "ℹ️ Yordam", "🔑 Admin Panel"]: 
        return
        
    word = m.text.strip().lower()
    
    # Faollikni va bazani yangilash
    update_user_activity(m.from_user)
    increment_search_count(m.from_user.id)
    u_data = get_user_data(m.from_user.id)
    
    # Tarixni yangilash
    if word in u_data['history']: u_data['history'].remove(word)
    u_data['history'].insert(0, word)
    u_data['history'] = u_data['history'][:15]
    save_user_data(m.from_user.id, u_data)
    
    # 1. BAZADAN QIDIRISH (Kesh tekshiruvi)
    data = get_word_cache(word)
    
    if data:
        wait = await m.answer("⚡ <i>Xotiradan olinmoqda...</i>", parse_mode="HTML")
    else:
        wait = await m.answer("⏳ <i>Saytdan qidirilmoqda (Navbat kutilyapti)...</i>", parse_mode="HTML")
        sem = await get_semaphore()
        async with sem: # MAX 10 ta so'rov qoidasi
            data = await asyncio.to_thread(scrape_longman_ultimate, word)
            if data:
                save_word_cache(word, data) # Kelajak uchun bazaga saqlab qo'yamiz
                
    await wait.delete()
    
    if not data: return await m.answer(f"❌ <b>{word}</b> so'zi lug'atdan topilmadi.", parse_mode="HTML")
    
    TEMP_CACHE[m.chat.id] = data
    await m.answer(
        f"📦 <b>{word.upper()}</b> uchun bo'limni tanlang:\n\n"
        f"<i>Ma'nolarni ko'rish uchun pastdagi turkumlardan birini bosing.</i>", 
        reply_markup=get_parts_kb(data.keys()), parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("v_"))
async def process_view(call: types.CallbackQuery):
    await call.answer()
    choice = call.data.replace("v_", "")
    data = TEMP_CACHE.get(call.message.chat.id)
    u_data = get_user_data(call.from_user.id)
    
    if not data: return await call.message.answer("⚠️ Ma'lumot eskirgan, so'zni qayta qidiring.")
    
    prog = await call.message.edit_text("🔍")
    for em in ["🎗", "✍️", "⌛"]:
        await asyncio.sleep(0.3)
        try: await prog.edit_text(em)
        except: pass
    
    if choice == "all":
        full_text = ""
        for pos, content in data.items():
            full_text += format_output(pos, content, u_data['show_examples'], u_data['show_translation']) + "═"*15 + "\n"
        await send_sequential_messages(call.message, full_text)
    else:
        await send_sequential_messages(call.message, format_output(choice, data[choice], u_data['show_examples'], u_data['show_translation']))
    
    try: await prog.delete()
    except: pass

# ==========================================
# --- 5. BOT YONGANDA AUTO-SCRAPERNI YOG'ISH ---
# ==========================================
@dp.startup()
async def on_startup(dispatcher: Dispatcher):
    # Bot ishga tushishi bilan auto_fill_database orqa fonda parallel boshlanadi
    start_scraper_thread()
