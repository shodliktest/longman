def get_welcome_msg(name):
    return (
        f"👋 <b>Salom, {name}!</b>\n\n"
        f"📕 <b>Longman Ultimate Pro</b> botiga xush kelibsiz.\n"
        f"Menga istalgan inglizcha so'zni yuboring, men uning barcha ma'nolari, transkripsiyasi va misollarini keltirib beraman.\n\n"
        f"⚙️ <b>Eslatma:</b> Pastdagi <i>Sozlamalar</i> menyusi orqali inglizcha misollarni o'chirib qo'yishingiz yoki <b>O'zbekcha tarjimani</b> yoqishingiz mumkin!\n\n"
        f"🚀 <i>Hoziroq biror so'z yozib yuboring!</i>"
    )

HELP_MSG = (
    "📚 <b>Yordam paneli:</b>\n\n"
    "1️⃣ <b>So'z qidirish:</b> Menga istalgan inglizcha so'z yuboring.\n"
    "2️⃣ <b>Tarix:</b> Siz oldin qidirgan oxirgi 15 ta so'z ro'yxati.\n"
    "3️⃣ <b>Sozlamalar:</b> Inglizcha misollarni va O'zbekcha tarjimani yoqib/o'chirib qo'yishingiz mumkin."
)

def get_new_user_admin_msg(full_name, user_id, username, joined_time):
    return (
        f"🆕 <b>YANGI FOYDALANUVCHI:</b>\n\n"
        f"👤 <b>Ism:</b> {full_name}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"⏰ <b>Vaqt:</b> {joined_time}"
    )
