import os
import json
import logging
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from openai import AsyncOpenAI

# ----------------- CONFIG -----------------
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

ADMIN_IDS_RAW = (os.getenv("ADMIN_IDS") or "").strip()
ADMIN_IDS: List[int] = []
if ADMIN_IDS_RAW:
    for x in ADMIN_IDS_RAW.split(","):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.append(int(x))

ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

STATE_FILE = "state.json"
DEFAULT_STATE = {
    "promo_enabled": True,
    "promo_text": (
        "🚖 Mashjid Nabaviydan Uhud tog‘iga (yoki boshqa ziyoratlarga) qulay borish uchun "
        "biz sizga arzon va ishonchli taksilarni topib beramiz.\n"
        "🌿 Ali Attar: uzoq saqlanadigan premium attarlar ham bor. Aloqa: @Ali_Attar0_bot"
    ),
}

SYSTEM_PROMPT = """
Siz “Ziyorat & Umra” bo‘limi uchun AI yordamchisiz.
Vazifangiz: foydalanuvchiga Madina va Makka bo‘yicha ziyorat/umra/ibodat haqida foydali, qiziqarli, adabli va ishonchli tarzda tushuntirish.

Qoidalar:
- Javob tili: o‘zbek (lotin). Juda tushunarli va iliq ohangda yozing.
- Keraksiz uzoq bo‘lmang, lekin foydali bo‘ling: 6–14 ta punkt/band atrofida.
- Diniy masalalarda “fatvo” berib yubormang: “aniq masalada ulamoga/ishonchli manbaga murojaat qiling” deb muloyim eslatib qo‘ying.
- So‘rovga mos qilib aniq reja bering (masalan: “Madinaga keldingizmi — 3 kun ichida …”).
- Miqot, ehrom, niyat, talbiya, ehromdagi taqiqlar, odoblar, ziyorat joylari tarixi haqida qisqa-qisqa qiziqarli faktlar qo‘shing.
- Javobning O‘RTASIDA yoki OXIRIDA juda silliq 1–2 qator reklama qo‘shing (spamsiz):
  1) “Mashjid Nabaviy → Uhud” yoki “ziyorat joylariga” borish uchun arzon taxi topib berish xizmati borligini ayting.
  2) Ali Attar attarlari borligini ayting.
  3) Aloqa: @Ali_Attar0_bot
- Reklama matni doim muloyim, foydali kontekstda bo‘lsin.
""".strip()

# ----------------- LOGGING -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("umra_ai_bot")

# ----------------- STATE -----------------
def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        s = DEFAULT_STATE.copy()
        s.update(data if isinstance(data, dict) else {})
        return s
    except Exception:
        return DEFAULT_STATE.copy()

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("State save failed: %s", e)

STATE = load_state()

# ----------------- HELPERS -----------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def chat_allowed(chat_id: int) -> bool:
    if ALLOWED_CHAT_ID is None:
        return True
    return chat_id == ALLOWED_CHAT_ID

def build_admin_kb():
    promo_status = "✅ ON" if STATE.get("promo_enabled", True) else "⛔ OFF"
    kb = [
        [InlineKeyboardButton(f"Promo: {promo_status}", callback_data="adm:toggle_promo")],
        [InlineKeyboardButton("✏️ Promo matnini ko‘rish", callback_data="adm:show_promo")],
        [InlineKeyboardButton("🧹 Promo matnini defaultga qaytarish", callback_data="adm:reset_promo")],
    ]
    return InlineKeyboardMarkup(kb)

def inject_promo(answer: str) -> str:
    if not bool(STATE.get("promo_enabled", True)):
        return answer
    promo = (STATE.get("promo_text") or "").strip()
    return f"{answer}\n\n—\n{promo}" if promo else answer

# ----------------- OPENAI -----------------
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def ask_ai(user_text: str) -> str:
    if not client:
        return "❗ OPENAI_API_KEY qo‘yilmagan. Railway Variables’ga OPENAI_API_KEY ni kiriting."

    try:
        resp = await client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.7,
        )
        out = []
        for item in resp.output:
            if getattr(item, "type", None) == "message":
                for c in item.content:
                    if getattr(c, "type", None) == "output_text":
                        out.append(c.text)
        text = ("\n".join(out)).strip()
        return text or "Kechirasiz, javob chiqarmadim. Savolni boshqacha yozib ko‘ring."
    except Exception as e:
        log.exception("OpenAI error: %s", e)
        return "❗ AI serverda xatolik bo‘ldi. Birozdan so‘ng qayta urinib ko‘ring."

# ----------------- HANDLERS -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    msg = (
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha yordamchi botman.\n\n"
        "Savol yozing, masalan:\n"
        "• “Madinaga keldim, 3 kunda qayerlarga boray?”\n"
        "• “Miqotda nima qilinadi, qanday niyat?”\n"
        "• “Ehromda nimalar mumkin emas?”\n\n"
        "Admin bo‘lsangiz: /admin"
    )
    await update.message.reply_text(msg)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return
    await update.message.reply_text("🛠 Admin panel:", reply_markup=build_admin_kb())

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.from_user:
        return
    if not is_admin(q.from_user.id):
        await q.answer("⛔ Admin emas", show_alert=True)
        return

    data = q.data or ""
    if data == "adm:toggle_promo":
        STATE["promo_enabled"] = not bool(STATE.get("promo_enabled", True))
        save_state(STATE)
        await q.answer("OK")
        await q.edit_message_reply_markup(reply_markup=build_admin_kb())

    elif data == "adm:show_promo":
        await q.answer("OK")
        await q.message.reply_text(f"📣 Promo matni:\n\n{STATE.get('promo_text','')}")

    elif data == "adm:reset_promo":
        STATE["promo_text"] = DEFAULT_STATE["promo_text"]
        save_state(STATE)
        await q.answer("OK")
        await q.message.reply_text("✅ Promo defaultga qaytarildi.")
        await q.edit_message_reply_markup(reply_markup=build_admin_kb())

async def setpromo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return
    parts = (update.message.text or "").split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("Foydalanish: /setpromo <yangi promo matn>")
        return
    STATE["promo_text"] = parts[1].strip()
    save_state(STATE)
    await update.message.reply_text("✅ Promo matni yangilandi.")

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    user_text = (update.message.text or "").strip()
    if not user_text:
        return
    if len(user_text) > 4000:
        user_text = user_text[:4000]

    await update.message.chat.send_action("typing")
    answer = await ask_ai(user_text)
    await update.message.reply_text(inject_promo(answer))

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables’ga BOT_TOKEN qo‘ying.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("setpromo", setpromo_cmd))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^adm:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_message))

    log.info("✅ Umra AI bot ishga tushdi. Adminlar: %s | Allowed chat: %s", ADMIN_IDS, ALLOWED_CHAT_ID)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
