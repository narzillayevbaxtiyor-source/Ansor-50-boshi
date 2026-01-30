import os
import json
import logging
from typing import Dict, Any, Optional

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

# ----------------- CONFIG -----------------
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").strip().lstrip("@")  # e.g. Ali_Attar0_bot

ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID: Optional[int] = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

STATE_FILE = "state.json"

# ----------------- LOGGING -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("umra_faq_bot")

# ----------------- STATE -----------------
DEFAULT_STATE: Dict[str, Any] = {
    "user_lang": {},  # { "user_id": "uz" or "kr" }
}

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return json.loads(json.dumps(DEFAULT_STATE))
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_STATE))
        # merge defaults
        s = json.loads(json.dumps(DEFAULT_STATE))
        s.update(data)
        if "user_lang" not in s or not isinstance(s["user_lang"], dict):
            s["user_lang"] = {}
        return s
    except Exception:
        return json.loads(json.dumps(DEFAULT_STATE))

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
    return STATE.get("user_lang", {}).get(str(user_id), "uz")  # default uz (lotin)

def set_lang(user_id: int, lang: str) -> None:
    if lang not in ("uz", "kr"):
        return
    STATE.setdefault("user_lang", {})
    STATE["user_lang"][str(user_id)] = lang
    save_state(STATE)

# ----------------- FAQ TEMPLATES -----------------
FAQ: Dict[str, Dict[str, str]] = {
    "madina_3kun": {
        "uz": (
            "🕌 *Madinaga keldingizmi? 3 kunlik qisqa reja*\n\n"
            "1) *Masjid Nabaviy* – salovot, Qur’on, adab bilan ko‘proq ibodat.\n"
            "2) *Rawza (Riyozul Janna)* – imkon bo‘lsa navbat/rezerv orqali kirish.\n"
            "3) *Baqiy’ qabristoni* – sahobalar xotirasi, duolar.\n"
            "4) *Uhud tog‘i* – Uhud voqealari, sabr va jihod saboqlari.\n"
            "5) *Qubo masjidi* – sunnat: borib 2 rakat namoz o‘qish.\n"
            "6) *Qiblatayn masjidi* – qibla o‘zgargan voqea esdaligi.\n\n"
            "✅ Eslatma: aniq ibodat-hukmlar bo‘yicha ishonchli ulamoga murojaat qiling.\n\n"
            "—\n"
            "🚖 Masjid Nabaviy → Uhud / Qubo / Qiblatayn borish uchun arzon taxi topib beramiz.\n"
            "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
        ),
        "kr": (
            "🕌 *Мадинага келдингизми? 3 кунлик қисқа режа*\n\n"
            "1) *Масжид Набавий* – саловот, Қуръон, адаб билан кўпроқ ибодат.\n"
            "2) *Равза (Риёзул Жанна)* – имкони бўлса навбат/резерв орқали кириш.\n"
            "3) *Бақийъ қабристони* – саҳобалар хотираси, дуолар.\n"
            "4) *Уҳуд тоғи* – Уҳуд воқеалари, сабр ва жиҳод сабоқлари.\n"
            "5) *Қубо масжиди* – суннат: бориб 2 ракат намоз ўқиш.\n"
            "6) *Қиблатайн масжиди* – қибла ўзгарган воқеа эсдалиги.\n\n"
            "✅ Эслатма: аниқ ибодат-ҳукмлар бўйича ишончли уламога мурожаат қилинг.\n\n"
            "—\n"
            "🚖 Масжид Набавий → Уҳуд / Қубо / Қиблатайн бориш учун арзон такси топиб берамиз.\n"
            "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
        ),
    },
    "miqot": {
        "uz": (
            "🧭 *Miqotda nima qilinadi?*\n\n"
            "1) Miqotga yetmasdan oldin *g‘usl* (bo‘lsa) va poklanish.\n"
            "2) *Ehrom* kiyish (erkaklar: 2 mato; ayollar: odobli, yopiq kiyim).\n"
            "3) *Niyat*: “Umra uchun ehromga kirdim…” mazmunida.\n"
            "4) *Talbiya*: “Labbaykallohumma labbayk…” ni ko‘p aytish.\n"
            "5) Miqotdan *ehromsiz* o‘tib ketmaslik (zarurat bo‘lsa, ulamodan so‘rang).\n\n"
            "—\n"
            "🚖 Miqotdan keyin Makkaga qulay yetib borish uchun arzon taxi topib beramiz.\n"
            "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
        ),
        "kr": (
            "🧭 *Миқотда нима қилинади?*\n\n"
            "1) Миқотга етмасдан олдин *ғусл* (бўлса) ва покланиш.\n"
            "2) *Эҳром* кийиш (эркаклар: 2 мато; аёллар: одобли, ёпиқ кийим).\n"
            "3) *Ният*: “Умра учун эҳромга кирдим…” мазмунида.\n"
            "4) *Талбия*: “Лаббайкаллоҳумма лаббайк…” ни кўп айтиш.\n"
            "5) Миқотдан *эҳромсиз* ўтиб кетмаслик (зарурат бўлса, уламодан сўранг).\n\n"
            "—\n"
            "🚖 Миқотдан кейин Маккага қулай етиб бориш учун арзон такси топиб берамиз.\n"
            "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
        ),
    },
    "ehrom_taqiqlar": {
        "uz": (
            "⛔ *Ehromdagi asosiy taqiqlar (qisqa)*\n\n"
            "1) Atir sepish (ehromga kirgach).\n"
            "2) Soch/soqol olish, tirnoq olish.\n"
            "3) Jinsiy yaqinlik va bunga olib boruvchi ishlar.\n"
            "4) Ov qilish.\n"
            "5) Erkaklarga: tikilgan kiyim, boshni yopish.\n"
            "6) Ayollarga: niqob/qo‘lqop (fiqh tafsiloti bor — ulamodan so‘rang).\n\n"
            "✅ Tafsilotlar mazhabga ko‘ra farq qilishi mumkin.\n\n"
            "—\n"
            "🚖 Ziyorat joylariga tartibli borib-kelish uchun arzon taxi topib beramiz.\n"
            "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
        ),
        "kr": (
            "⛔ *Эҳромдаги асосий тақиқлар (қисқа)*\n\n"
            "1) Аттир сепиш (эҳромга киргач).\n"
            "2) Соч/соқол олиш, тирноқ олиш.\n"
            "3) Жинсий яқинлик ва бунга олиб борувчи ишлар.\n"
            "4) Ов қилиш.\n"
            "5) Эркакларга: тикilgan кийим, бошни ёпиш.\n"
            "6) Аёлларга: ниқоб/қўлқоп (фиқҳ тафсилоти бор — уламодан сўранг).\n\n"
            "✅ Тафсилотлар мазҳабга кўра фарқ қилиши мумкин.\n\n"
            "—\n"
            "🚖 Зиёрат жойларига тартибли бориб-келиш учун арзон такси топиб берамиз.\n"
            "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
        ),
    },
}

# optional triggers if user writes exact text in group
TRIGGERS = {
    "madina_3kun": [
        "madinaga keldim, 3 kunda qayerlarga boray?",
        "мадинага келдим, 3 кунда қаерларга борай?",
    ],
    "miqot": [
        "miqotda nima qilinadi?",
        "миқотда нима қилинади?",
    ],
    "ehrom_taqiqlar": [
        "ehromda nimalar mumkin emas?",
        "эҳромда нималар мумкин эмас?",
    ],
}

# ----------------- UI BUILDERS -----------------
def deep_link(key: str) -> Optional[str]:
    if not BOT_USERNAME:
        return None
    return f"https://t.me/{BOT_USERNAME}?start=faq_{key}"

def kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 UZ (lotin)", callback_data="lang:uz")],
        [InlineKeyboardButton("🇺🇿 KRIL", callback_data="lang:kr")],
    ])

def kb_faq_private() -> InlineKeyboardMarkup:
    # private chat: callback buttons (fast)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Madina 3 kunlik reja", callback_data="faq:madina_3kun")],
        [InlineKeyboardButton("🧭 Miqotda nima qilinadi?", callback_data="faq:miqot")],
        [InlineKeyboardButton("⛔ Ehromdagi taqiqlar", callback_data="faq:ehrom_taqiqlar")],
    ])

def kb_faq_deeplink() -> InlineKeyboardMarkup:
    # group: URL deep links so it opens DM
    rows = []
    for key, title in [
        ("madina_3kun", "📍 Madina 3 kunlik reja"),
        ("miqot", "🧭 Miqotda nima qilinadi?"),
        ("ehrom_taqiqlar", "⛔ Ehromdagi taqiqlar"),
    ]:
        url = deep_link(key)
        if url:
            rows.append([InlineKeyboardButton(title, url=url)])
    if not rows:
        rows = [[InlineKeyboardButton("Botga yozish (DM)", callback_data="noop")]]
    return InlineKeyboardMarkup(rows)

def render_faq(key: str, lang: str) -> str:
    item = FAQ.get(key)
    if not item:
        return "Topilmadi."
    return item.get(lang, item.get("uz", "Topilmadi."))

# ----------------- HANDLERS -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    user_id = update.effective_user.id

    # /start payload like: faq_madina_3kun
    payload = ""
    if context.args:
        payload = (context.args[0] or "").strip()

    # If payload is faq_...
    if payload.startswith("faq_"):
        key = payload.replace("faq_", "", 1).strip()
        lang = get_lang(user_id)
        txt = render_faq(key, lang)
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    # normal start
    greet_uz = (
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha *tayyor javoblar* botiman.\n\n"
        "Tilni tanlang va kerakli mavzuni bosing 👇"
    )
    greet_kr = (
        "Ассалому алайкум! 🤍\n"
        "Мен Умра & Зиёрат бўйича *тайёр жавоблар* ботиман.\n\n"
        "Тилни танланг ва керакли мавзuni босинг 👇"
    )

    lang = get_lang(user_id)
    greet = greet_uz if lang == "uz" else greet_kr

    await update.message.reply_text(greet, parse_mode="Markdown", reply_markup=kb_language())
    await update.message.reply_text("📚 Mavzular:", reply_markup=kb_faq_private())

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()

    user_id = q.from_user.id
    data = q.data or ""

    if data.startswith("lang:"):
        lang = data.split(":", 1)[1].strip()
        set_lang(user_id, lang)
        await q.message.reply_text("✅ Til saqlandi." if lang == "uz" else "✅ Тил сақланди.")
        return

    if data.startswith("faq:"):
        key = data.split(":", 1)[1].strip()
        lang = get_lang(user_id)
        txt = render_faq(key, lang)
        await q.message.reply_text(txt, parse_mode="Markdown")
        return

async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Groupda kimdir savol yozsa:
    - Bot uni o‘chiradi (huquqi bo‘lsa)
    - DMga o‘tish uchun URL tugmalar tashlaydi (deep link + start payload)
    """
    if not update.effective_chat or not update.message or not update.effective_user:
        return
    chat = update.effective_chat
    if not chat_allowed(chat.id):
        return

    # Only in groups/supergroups
    if chat.type not in ("group", "supergroup"):
        return

    text = (update.message.text or "").strip()
    norm = text.lower()

    # try delete
    try:
        await update.message.delete()
    except Exception:
        pass  # bot admin bo‘lmasa o‘chira olmaydi

    # if matches a known trigger, send a direct deep link for that answer
    matched_key = None
    for key, variants in TRIGGERS.items():
        for v in variants:
            if norm == v.lower():
                matched_key = key
                break
        if matched_key:
            break

    if matched_key and deep_link(matched_key):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Javobni olish (shaxsiy)", url=deep_link(matched_key))],
            [InlineKeyboardButton("📚 Boshqa mavzular", url=f"https://t.me/{BOT_USERNAME}?start=menu")] if BOT_USERNAME else [],
        ])
        # remove empty rows
        kb.inline_keyboard = [row for row in kb.inline_keyboard if row]
        await chat.send_message(
            "Savol shaxsiyda javoblanadi 👇",
            reply_markup=kb
        )
        return

    # default: show FAQ buttons that open DM with start payloads
    await chat.send_message(
        "Savollar shaxsiyda (DM) javoblanadi. Quyidan mavzuni tanlang 👇",
        reply_markup=kb_faq_deeplink()
    )

# ----------------- MAIN -----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q. Railway Variables’ga BOT_TOKEN kiriting.")
    if not BOT_USERNAME:
        log.warning("BOT_USERNAME yo‘q. Deep-link ishlashi uchun BOT_USERNAME kiriting (masalan Ali_Attar0_bot).")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    # group text -> delete + DM buttons
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))

    log.info("✅ Umra FAQ bot ishga tushdi | Allowed chat: %s | Username: %s", ALLOWED_CHAT_ID, BOT_USERNAME)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
