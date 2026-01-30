import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").strip().lstrip("@")

TRANSPORT_URL = "https://t.me/saudia0dan_group/199"

ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID: Optional[int] = (
    int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None
)

STATE_FILE = "state.json"

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("umra_faq_bot")

# ================= STATE =================
DEFAULT_STATE: Dict[str, Any] = {
    "user_lang": {}
}

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return DEFAULT_STATE.copy()
        s = DEFAULT_STATE.copy()
        s.update(data)
        return s
    except Exception:
        return DEFAULT_STATE.copy()

def save_state(state: Dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("State save failed: %s", e)

STATE = load_state()

def chat_allowed(chat_id: int) -> bool:
    if ALLOWED_CHAT_ID is None:
        return True
    return chat_id == ALLOWED_CHAT_ID

def get_lang(user_id: int) -> str:
    return STATE.get("user_lang", {}).get(str(user_id), "uz")

def set_lang(user_id: int, lang: str) -> None:
    if lang not in ("uz", "kr"):
        return
    STATE.setdefault("user_lang", {})
    STATE["user_lang"][str(user_id)] = lang
    save_state(STATE)

# ================= FAQ DATABASE =================
FAQ_DB: Dict[str, Tuple[str, str, str, str]] = {}

def add_faq(key: str, title_uz: str, title_kr: str, text_uz: str, text_kr: str):
    FAQ_DB[key] = (title_uz, title_kr, text_uz, text_kr)

# -------- MIQOT --------
add_faq(
    "miqot",
    "🧭 Miqotda nima qilinadi?",
    "🧭 Миқотда нима қилинади?",
    (
        "🧭 *Miqotda nima qilinadi?*\n\n"
        "1) Miqotga yetmasdan oldin g‘usl va poklanish.\n"
        "2) Ehrom kiyish.\n"
        "3) Niyat qilish.\n"
        "4) Talbiya aytish.\n"
        "5) Ehromsiz miqotdan o‘tib ketmaslik.\n\n"
        "—\n"
        "🚖 Miqotdan keyin Makkaga qulay borish uchun arzon taxi topib beramiz.\n"
        f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n"
        "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    (
        "🧭 *Миқотда нима қилинади?*\n\n"
        "1) Ғусл ва покланиш.\n"
        "2) Эҳром кийиш.\n"
        "3) Ният қилиш.\n"
        "4) Талбия айтиш.\n"
        "5) Эҳромсиз ўтиб кетмаслик.\n\n"
        "—\n"
        "🚖 Миқотдан кейин Маккага арзон такси топиб берамиз.\n"
        f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n"
        "🌿 Ali Attar аттарлари бор. Алоқа: @Ali_Attar0_bot"
    ),
)

# -------- MADINA 3 KUN --------
add_faq(
    "madina_3kun",
    "📍 Madina 3 kunlik reja",
    "📍 Мадина 3 кунлик режа",
    (
        "🕌 *Madinaga keldingizmi? 3 kunlik reja*\n\n"
        "1) Masjid Nabaviy\n"
        "2) Rawza\n"
        "3) Baqi’\n"
        "4) Uhud\n"
        "5) Qubo\n"
        "6) Qiblatayn\n\n"
        "—\n"
        "🚖 Ziyorat joylariga qulay borish uchun arzon taxi topib beramiz.\n"
        f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n"
        "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    (
        "🕌 *Мадинага келдингизми? 3 кунлик режа*\n\n"
        "1) Масжид Набавий\n"
        "2) Равза\n"
        "3) Бақийъ\n"
        "4) Уҳуд\n"
        "5) Қубо\n"
        "6) Қиблатайн\n\n"
        "—\n"
        "🚖 Зиёрат жойларига арзон такси топиб берамиз.\n"
        f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n"
        "🌿 Ali Attar аттарлари бор. Алоқа: @Ali_Attar0_bot"
    ),
)# ================= UI =================
def deep_link(key: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=faq_{key}"

def kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 UZ (lotin)", callback_data="lang:uz")],
        [InlineKeyboardButton("🇺🇿 KRIL", callback_data="lang:kr")],
    ])

def kb_faq_deeplink() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧭 Miqotda nima qilinadi?", url=deep_link("miqot"))],
        [InlineKeyboardButton("📍 Madina 3 kunlik reja", url=deep_link("madina_3kun"))],
    ])

def render_faq(key: str, lang: str) -> str:
    item = FAQ_DB.get(key)
    if not item:
        return "Topilmadi."
    _, _, uz, kr = item
    return uz if lang == "uz" else kr

# ================= HANDLERS =================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = update.effective_user.id
    payload = context.args[0] if context.args else ""

    if payload.startswith("faq_"):
        key = payload.replace("faq_", "")
        txt = render_faq(key, get_lang(user_id))
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    await update.message.reply_text(
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha yordamchiman.\n\n"
        "Tilni tanlang 👇",
        reply_markup=kb_language()
    )
    await update.message.reply_text(
        "📌 Mavzular:",
        reply_markup=kb_faq_deeplink()
    )

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("lang:"):
        lang = q.data.split(":")[1]
        set_lang(q.from_user.id, lang)
        await q.message.reply_text("✅ Til saqlandi.")

async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(
        "Savollar shaxsiyda javoblanadi 👇",
        reply_markup=kb_faq_deeplink()
    )

# ================= MAIN =================
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))

    log.info("✅ Umra & Ziyorat FAQ bot ishga tushdi")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
