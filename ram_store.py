"""
ram_store.py — Process darajasidagi RAM xotira.

Bu modul Python interpreter tomonidan faqat BIR MARTA yuklanadi.
Streamlit rerun, sahifa yangilash, brauzer yopish — hech narsaga ta'sir qilmaydi.
Faqat server reboot bo'lganda o'chadi.
"""

import threading
import datetime

# ──────────────────────────────────────────────
#  SINGLETON: modul import qilinganda bir marta
#  ishga tushadi, qayta yuklanmaydi.
# ──────────────────────────────────────────────

_lock = threading.Lock()

_store = {
    "words":        [],    # [ "hello", "world", ... ]
    "total":        0,     # jami so'zlar soni (o'zgarmaydi)
    "remaining":    0,     # qolgan so'zlar soni
    "uploaded_at":  None,  # yuklangan vaqt (str)
    "source":       None,  # "telegram" | "web"
}


# ─────────────── WRITE ───────────────

def set_words(words: list, source: str = "web"):
    """Yangi so'zlar ro'yxatini RAM ga saqlaydi."""
    with _lock:
        _store["words"]       = list(words)
        _store["total"]       = len(words)
        _store["remaining"]   = len(words)
        _store["uploaded_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _store["source"]      = source
    print(f"[RAM] ✅ {len(words)} ta so'z saqlandi. Manba: {source}")


def pop_word() -> str | None:
    """Ro'yxatdan birinchi so'zni olib, uni o'chiradi (FIFO)."""
    with _lock:
        if _store["words"]:
            word = _store["words"].pop(0)
            _store["remaining"] = len(_store["words"])
            return word
        return None


def remove_word(word: str):
    """Muayyan so'zni ro'yxatdan olib tashlaydi."""
    with _lock:
        try:
            _store["words"].remove(word)
            _store["remaining"] = len(_store["words"])
        except ValueError:
            pass


def clear():
    """RAM ni to'liq tozalaydi."""
    with _lock:
        _store["words"]       = []
        _store["total"]       = 0
        _store["remaining"]   = 0
        _store["uploaded_at"] = None
        _store["source"]      = None
    print("[RAM] 🗑 Cache tozalandi.")


# ─────────────── READ ───────────────

def get_words() -> list:
    """Qolgan so'zlar nusxasini qaytaradi."""
    with _lock:
        return list(_store["words"])


def has_words() -> bool:
    with _lock:
        return len(_store["words"]) > 0


def get_info() -> dict:
    """Admin panel uchun holat ma'lumotlari."""
    with _lock:
        return {
            "total":       _store["total"],
            "remaining":   _store["remaining"],
            "done":        _store["total"] - _store["remaining"],
            "uploaded_at": _store["uploaded_at"] or "—",
            "source":      _store["source"] or "—",
            "preview":     list(_store["words"][:20]),
        }
