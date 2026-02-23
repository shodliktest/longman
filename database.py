import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

UZ_TZ = pytz.timezone('Asia/Tashkent')

def get_uz_time():
    return datetime.now(UZ_TZ).strftime('%Y-%m-%d %H:%M:%S')

if not firebase_admin._apps:
    try:
        cred_dict = dict(st.secrets["firebase"]) if "firebase" in st.secrets else dict(st.secrets)
        if "private_key" in cred_dict:
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Firebase xatosi: {e}")
        st.stop()

try:
    db = firestore.client()
except Exception as e:
    st.error(f"❌ Firestore ulanish xatosi: {e}")
    st.stop()

# --- FOYDALANUVCHI BAZASI ---
def get_user_data(user_id):
    try:
        doc = db.collection('users').document(str(user_id)).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                "history": data.get("history", []),
                "show_examples": data.get("show_examples", True),
                "show_translation": data.get("show_translation", False)
            }
    except: pass
    return {"history": [], "show_examples": True, "show_translation": False}

def save_user_data(user_id, user_dict):
    try:
        db.collection('users').document(str(user_id)).set(user_dict, merge=True)
    except: pass

def update_user_activity(user):
    try:
        user_ref = db.collection('users').document(str(user.id))
        doc = user_ref.get()
        now = get_uz_time()
        today = now[:10] # Faqat sanani olamiz
        username = f"@{user.username}" if user.username else "Mavjud emas"
        
        if not doc.exists:
            user_ref.set({
                "id": str(user.id),
                "name": user.full_name,
                "username": username,
                "joined_at": now,
                "last_active": now,
                "search_count": 0,
                "history": [],
                "show_examples": True,
                "show_translation": False
            })
            
            # 1. Umumiy userlar sonini oshirish (Counter)
            stat_ref = db.collection('settings').document('stats')
            if not stat_ref.get().exists:
                stat_ref.set({"total_searches": 0, "page_views": 0, "total_users": 1})
            else:
                stat_ref.update({"total_users": firestore.Increment(1)})
                
            # 2. Grafik uchun kunlik userlar o'sishini yozish (Tejamkor)
            db.collection('daily_user_stats').document(today).set({
                "count": firestore.Increment(1)
            }, merge=True)
            
            return True 
        else:
            user_ref.update({
                "name": user.full_name,
                "username": username,
                "last_active": now
            })
            return False
    except: return False

def increment_search_count(user_id):
    try:
        db.collection('users').document(str(user_id)).update({
            "search_count": firestore.Increment(1)
        })
        stat_ref = db.collection('settings').document('stats')
        if not stat_ref.get().exists:
            stat_ref.set({"total_searches": 0, "page_views": 0})
        stat_ref.update({"total_searches": firestore.Increment(1)})
    except: pass

def get_all_users(limit_count=50):
    # LIMIT QO'SHILDI: Endi jadval uchun faqat oxirgi 50 ta userni tortamiz!
    try:
        docs = db.collection('users').order_by('joined_at', direction=firestore.Query.DESCENDING).limit(limit_count).stream()
        return [doc.to_dict() for doc in docs]
    except: return []

def get_stats():
    try:
        doc = db.collection('settings').document('stats').get()
        if doc.exists: return doc.to_dict()
    except: return {}

def increment_page_view():
    try:
        stat_ref = db.collection('settings').document('stats')
        if not stat_ref.get().exists: stat_ref.set({"total_searches": 0, "page_views": 0})
        stat_ref.update({"page_views": firestore.Increment(1)})
    except: pass

# --- SO'ZLAR KESHI (TEZKOR ISHLASH UCHUN) ---
def save_word_cache(word, data):
    """Qidirilgan so'zni saqlash va GRAFIK uchun kunlik hisobni yuritish"""
    try:
        now = get_uz_time()
        today = now[:10] # Faqat sanani olamiz (YYYY-MM-DD)
        
        # 1. So'zni o'zini saqlaymiz
        db.collection('word_cache').document(word.lower()).set({
            'data': data,
            'created_at': now
        })
        
        # 2. GRAFIK UCHUN: Bugungi kunga +1 ta so'z qo'shamiz (Tejamkor hisobchi)
        db.collection('daily_word_stats').document(today).set({
            "count": firestore.Increment(1)
        }, merge=True)
        
    except: pass

def get_word_cache(word):
    """So'z avval qidirilgan bo'lsa, uni yashin tezligida bazadan olish"""
    try:
        doc = db.collection('word_cache').document(word.lower()).get()
        if doc.exists:
            return doc.to_dict().get('data')
    except: pass
    return None

def get_daily_word_stats():
    """Admin panel grafigi uchun kunlik o'sish tarixini olish"""
    try:
        docs = db.collection('daily_word_stats').stream()
        return [{"date": doc.id, "count": doc.to_dict().get("count", 0)} for doc in docs]
    except: return []

def get_daily_user_stats():
    """Admin panel grafigi uchun kunlik userlar o'sish tarixini olish"""
    try:
        docs = db.collection('daily_user_stats').stream()
        return [{"date": doc.id, "count": doc.to_dict().get("count", 0)} for doc in docs]
    except: return []
