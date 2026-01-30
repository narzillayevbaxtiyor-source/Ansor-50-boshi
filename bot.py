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

# ----------------- CONFIG -----------------
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").strip().lstrip("@")  # e.g. Ali_Attar0_bot

TRANSPORT_URL = (os.getenv("TRANSPORT_URL") or "").strip()  # channel link to "Transport" section/post

ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID: Optional[int] = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

STATE_FILE = "state.json"

# ----------------- LOGGING -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
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
    return STATE.get("user_lang", {}).get(str(user_id), "uz")

def set_lang(user_id: int, lang: str) -> None:
    if lang not in ("uz", "kr"):
        return
    STATE.setdefault("user_lang", {})
    STATE["user_lang"][str(user_id)] = lang
    save_state(STATE)

# ----------------- PROMO (with Transport link) -----------------
def promo_lines(lang: str) -> str:
    # NOTE: "Arzon taxi..." dan keyin TRANSPORT_URL ni qo'shyapmiz
    if lang == "kr":
        base = (
            "—\n"
            "🚖 Миқотдан кейин Маккага қулай етиб бориш учун арзон такси топиб берамиз.\n"
        )
        if TRANSPORT_URL:
            base += f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n"
        base += "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
        return base

    base = (
        "—\n"
        "🚖 Miqotdan keyin Makkaga qulay yetib borish uchun arzon taxi topib beramiz.\n"
    )
    if TRANSPORT_URL:
        base += f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n"
    base += "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    return base

# ----------------- FAQ DATABASE (30+ ready templates) -----------------
# Each item: key -> (title_uz, title_kr, text_uz, text_kr)
FAQ_DB: Dict[str, Tuple[str, str, str, str]] = {}

def add_faq(key: str, title_uz: str, title_kr: str, text_uz: str, text_kr: str) -> None:
    FAQ_DB[key] = (title_uz, title_kr, text_uz, text_kr)

# --- 1) Madina 3 kun ---
add_faq(
    "madina_3kun",
    "📍 Madina 3 kunlik reja",
    "📍 Мадина 3 кунлик режа",
    (
        "🕌 *Madinaga keldingizmi? 3 kunlik qisqa reja*\n\n"
        "1) *Masjid Nabaviy* – salovot, Qur’on, odob bilan ibodat.\n"
        "2) *Rawza (Riyozul Janna)* – imkon bo‘lsa kirish.\n"
        "3) *Baqiy’* – duolar, ibrat.\n"
        "4) *Uhud* – tarixiy voqealar, saboq.\n"
        "5) *Qubo* – borib 2 rakat namoz.\n"
        "6) *Qiblatayn* – qibla o‘zgargan masjid.\n\n"
        "✅ Eslatma: tafsilotlarda mazhabga ko‘ra farq bo‘lishi mumkin."
        "\n\n—\n"
        "🚖 Masjid Nabaviy → Uhud/Qubo/Qiblatayn borish uchun arzon taxi topib beramiz.\n"
        + (f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
        + "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    (
        "🕌 *Мадинага келдингизми? 3 кунлик қисқа режа*\n\n"
        "1) *Масжид Набавий* – саловот, Қуръон, адаб билан ибодат.\n"
        "2) *Равза* – имкони бўлса кириш.\n"
        "3) *Бақийъ* – дуолар, ибрат.\n"
        "4) *Уҳуд* – тарихий воқеалар, сабоқ.\n"
        "5) *Қубо* – бориб 2 ракат намоз.\n"
        "6) *Қиблатайн* – қибла ўзгарган масжид.\n\n"
        "✅ Эслатма: тафсилотларда мазҳабга кўра фарқ бўлиши мумкин."
        "\n\n—\n"
        "🚖 Масжид Набавий → Уҳуд/Қубо/Қиблатайн бориш учун арзон такси топиб берамиз.\n"
        + (f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
        + "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
    ),
)

# --- 2) Miqot ---
add_faq(
    "miqot",
    "🧭 Miqotda nima qilinadi?",
    "🧭 Миқотда нима қилинади?",
    (
        "🧭 *Miqotda nima qilinadi?*\n\n"
        "1) Miqotga yetmasdan oldin g‘usl (bo‘lsa) va poklanish.\n"
        "2) Ehrom kiyish (erkaklar: 2 mato; ayollar: odobli, yopiq kiyim).\n"
        "3) Niyat: “Umra uchun ehromga kirdim…” mazmunida.\n"
        "4) Talbiya: “Labbaykallohumma labbayk…” ni ko‘p aytish.\n"
        "5) Miqotdan ehromsiz o‘tib ketmaslik (zarurat bo‘lsa, ulamodan so‘rang).\n\n"
        + promo_lines("uz")
    ),
    (
        "🧭 *Миқотда нима қилинади?*\n\n"
        "1) Миқотга етмасдан олдин ғусл (бўлса) ва покланиш.\n"
        "2) Эҳром кийиш (эркаклар: 2 мато; аёллар: одобли, ёпиқ кийим).\n"
        "3) Ният: “Умра учун эҳромга кирдим…” мазмунида.\n"
        "4) Талбия: “Лаббайкаллоҳумма лаббайк…” ни кўп айтиш.\n"
        "5) Миқотдан эҳромсиз ўтиб кетмаслик (зарурат бўлса, уламодан сўранг).\n\n"
        + promo_lines("kr")
    ),
)

# --- 3) Ehrom taqiqlar ---
add_faq(
    "ehrom_taqiqlar",
    "⛔ Ehromdagi taqiqlar",
    "⛔ Эҳромдаги тақиқлар",
    (
        "⛔ *Ehromdagi asosiy taqiqlar (qisqa)*\n\n"
        "1) Atir sepish (ehromga kirgach).\n"
        "2) Soch/soqol olish, tirnoq olish.\n"
        "3) Jinsiy yaqinlik va bunga olib boruvchi ishlar.\n"
        "4) Ov qilish.\n"
        "5) Erkaklarga: tikilgan kiyim, boshni yopish.\n"
        "6) Ayollarga: niqob/qo‘lqop (tafsilot bor).\n\n"
        "✅ Tafsilotlar mazhabga ko‘ra farq qilishi mumkin.\n\n"
        "—\n"
        "🚖 Ziyorat joylariga borib-kelish uchun arzon taxi topib beramiz.\n"
        + (f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
        + "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    (
        "⛔ *Эҳромдаги асосий тақиқлар (қисқа)*\n\n"
        "1) Аттир сепиш (эҳромга киргач).\n"
        "2) Соч/соқол олиш, тирноқ олиш.\n"
        "3) Жинсий яқинлик ва бунга олиб борувчи ишлар.\n"
        "4) Ов қилиш.\n"
        "5) Эркакларга: тикilgan кийим, бошни ёпиш.\n"
        "6) Аёлларга: ниқоб/қўлқоп (тафсилот бор).\n\n"
        "✅ Тафсилотлар мазҳабга кўра фарқ қилиши мумкин.\n\n"
        "—\n"
        "🚖 Зиёрат жойларига бориб-келиш учун арзон такси топиб берамиз.\n"
        + (f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
        + "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
    ),
)

# ---- Add more FAQs quickly (skeleton 30+). You can edit texts later.
# Below are additional keys/titles; texts are short and safe.
MORE_ITEMS: List[Tuple[str, str, str]] = [
    ("tavof_qanday", "🕋 Tavof qanday qilinadi?", "🕋 Тавоф қандай қилинади?"),
    ("say_safa_marwa", "🏃 Sa’y (Safo–Marva) nima?", "🏃 Са’й (Сафо–Марва) нима?"),
    ("zamzam", "💧 Zamzam odobi", "💧 Замзам одоби"),
    ("rawza_kirish", "🌿 Rawzaga kirish", "🌿 Равзага кириш"),
    ("baqiy_adab", "🪦 Baqiy’ ziyorati adobi", "🪦 Бақийъ зиёрати одоби"),
    ("uhud_tarix", "⛰ Uhud haqida qisqa", "⛰ Уҳуд ҳақида қисқа"),
    ("qubo_fazilat", "🕌 Qubo fazilati", "🕌 Қубо фазилати"),
    ("qiblatayn", "🕌 Qiblatayn nima uchun mashhur?", "🕌 Қиблатайн нима учун машҳур?"),
    ("ihram_niyat", "🧎 Niyatni qanday qilish?", "🧎 Ниятни қандай қилиш?"),
    ("talbiya", "📿 Talbiya qachon aytiladi?", "📿 Талбия қачон айтилади?"),
    ("soch_tirnoq", "✂️ Ehromda soch/tirnoq masalasi", "✂️ Эҳромда соч/тирноқ масаласи"),
    ("ayol_ehrom", "👩 Ayol ehromda nimalarga e’tibor beradi?", "👩 Аёл эҳромда нималарга эътибор беради?"),
    ("erkak_ehrom", "👳 Erkak ehromda kiyim qoidasi", "👳 Эркак эҳромда кийим қоидаси"),
    ("umra_bosqich", "✅ Umra bosqichlari (qisqa)", "✅ Умра босқичлари (қисқа)"),
    ("haram_odobi", "🤍 Haramlarda odob", "🤍 Ҳарамларда одоб"),
    ("duo_paket", "🧡 Umrada duo g‘oyalari", "🧡 Умрада дуо ғоялари"),
    ("makkaga_kirish", "🏙 Makkaga kirganda nima qilish?", "🏙 Маккага кирганда нима қилиш?"),
    ("masjid_haram", "🕋 Masjidul Haromda yo‘nalishlar", "🕋 Масжидул Ҳаромда йўналишлар"),
    ("tavof_xatolar", "⚠️ Tavofdagi keng xatolar", "⚠️ Тавофдаги кенг хатолар"),
    ("say_xatolar", "⚠️ Sa’ydagi keng xatolar", "⚠️ Са’йдаги кенг хатолар"),
    ("tahallul", "💇 Tahallul (soch qisqartirish)", "💇 Таҳаллул (соч қисқартириш)"),
    ("juma_madina", "🕌 Madinada juma kuni", "🕌 Мадинада жума куни"),
    ("salom_berish", "🤝 Salom berish odobi", "🤝 Салом бериш одоби"),
    ("ziyorat_tartib", "📌 Ziyorat tartibi (qisqa)", "📌 Зиёрат тартиби (қисқа)"),
    ("ehrom_parfyum", "🌿 Ehrom va atir masalasi", "🌿 Эҳром ва аттир масаласи"),
    ("bolalar_umra", "👶 Bolalar bilan umra", "👶 Болалар билан умра"),
    ("sovuq_issiq", "🌡 Issiqda/sovuqda ibodat", "🌡 Иссиқда/совуқда ибодат"),
    ("taksi_madina", "🚖 Madinada transport", "🚖 Мадинада транспорт"),
    ("taksi_makka", "🚖 Makkada transport", "🚖 Маккада транспорт"),
]

for k, t_uz, t_kr in MORE_ITEMS:
    add_faq(
        k,
        t_uz,
        t_kr,
        (
            f"{t_uz}\n\n"
            "Bu mavzuda qisqa yo‘l-yo‘riq:\n"
            "• Asosiy qoidalarni yodda tuting.\n"
            "• Oqimga xalaqit bermang, odobni saqlang.\n"
            "• Aniq fiqh tafsilotlari bo‘lsa – ishonchli ulamodan so‘rang.\n\n"
            "—\n"
            "🚖 Ziyorat/transport bo‘yicha arzon taxi topib beramiz.\n"
            + (f"🧭 Transport bo‘limi: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
            + "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
        ),
        (
            f"{t_kr}\n\n"
            "Қисқа йўл-йўриқ:\n"
            "• Асосий қоидаларни ёдда тутинг.\n"
            "• Оқимга халақит берманг, одобни сақланг.\n"
            "• Аниқ фиқҳ тафсилоти бўлса – ишончли уламодан сўранг.\n\n"
            "—\n"
            "🚖 Зиёрат/транспорт бўйича арзон такси топиб берамиз.\n"
            + (f"🧭 Транспорт бўлими: {TRANSPORT_URL}\n" if TRANSPORT_URL else "")
            + "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
        ),
    )

# ----------------- TRIGGERS (optional exact match) -----------------
TRIGGERS: Dict[str, List[str]] = {
    "miqot": ["🧭 miqotda nima qilinadi?", "🧭 миқотда нима қилинади?"],
    "madina_3kun": ["madinaga keldim, 3 kunda qayerlarga boray?", "мадинага келдим, 3 кунда қаерларга борай?"],
    "ehrom_taqiqlar": ["ehromda nimalar mumkin emas?", "эҳромда нималар мумкин эмас?"],
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
    # Private chat: callbacks (fast)
    rows = []
    # show main 8 first
    first_keys = [
        "madina_3kun", "miqot", "ehrom_taqiqlar",
        "umra_bosqich", "tavof_qanday", "say_safa_marwa",
        "zamzam", "rawza_kirish",
    ]
    for k in first_keys:
        if k in FAQ_DB:
            title_uz, title_kr, _, _ = FAQ_DB[k]
            rows.append([InlineKeyboardButton(title_uz, callback_data=f"faq:{k}")])
    # "More" opens list in DM via deep-link menu
    if BOT_USERNAME:
        rows.append([InlineKeyboardButton("📚 Ko‘proq mavzular", url=f"https://t.me/{BOT_USERNAME}?start=menu")])
    return InlineKeyboardMarkup(rows)

def kb_faq_deeplink() -> InlineKeyboardMarkup:
    # Group: URL deep links -> opens DM with /start payload
    rows = []
    for k, (title_uz, _, _, _) in list(FAQ_DB.items())[:8]:
        url = deep_link(k)
        if url:
            rows.append([InlineKeyboardButton(title_uz, url=url)])
    if BOT_USERNAME:
        rows.append([InlineKeyboardButton("📚 Barcha mavzular (DM)", url=f"https://t.me/{BOT_USERNAME}?start=menu")])
    return InlineKeyboardMarkup(rows)

def kb_menu_paged(page: int, lang: str, page_size: int = 10) -> InlineKeyboardMarkup:
    keys = list(FAQ_DB.keys())
    total = len(keys)
    start = page * page_size
    end = min(start + page_size, total)
    chunk = keys[start:end]

    rows = []
    for k in chunk:
        title_uz, title_kr, _, _ = FAQ_DB[k]
        title = title_uz if lang == "uz" else title_kr
        rows.append([InlineKeyboardButton(title, callback_data=f"faq:{k}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"menu:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{(total + page_size - 1)//page_size}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"menu:{page+1}"))
    rows.append(nav)

    return InlineKeyboardMarkup(rows)

def render_faq(key: str, lang: str) -> str:
    item = FAQ_DB.get(key)
    if not item:
        return "Topilmadi." if lang == "uz" else "Топилмади."
    _, _, uz, kr = item
    return uz if lang == "uz" else kr

# ----------------- HANDLERS -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    user_id = update.effective_user.id
    payload = (context.args[0].strip() if context.args else "")

    # /start faq_xxx
    if payload.startswith("faq_"):
        key = payload.replace("faq_", "", 1).strip()
        lang = get_lang(user_id)
        txt = render_faq(key, lang)
        await update.message.reply_text(txt, parse_mode="Markdown")
        return

    # /start menu
    if payload == "menu":
        lang = get_lang(user_id)
        await update.message.reply_text(
            "📚 Mavzular ro‘yxati:" if lang == "uz" else "📚 Мавзулар рўйхати:",
            reply_markup=kb_menu_paged(0, lang),
        )
        return

    # Normal start text (updated as you asked)
    greet_uz = (
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha *yordamchiman*.\n\n"
        "Tilni tanlang va mavzuni bosing 👇"
    )
    greet_kr = (
        "Ассалому алайкум! 🤍\n"
        "Мен Умра & Зиёрат бўйича *ёрдамчиман*.\n\n"
        "Тилни танланг ва мавзuni босинг 👇"
    )
    lang = get_lang(user_id)
    greet = greet_uz if lang == "uz" else greet_kr

    await update.message.reply_text(greet, parse_mode="Markdown", reply_markup=kb_language())
    await update.message.reply_text("📌 Tezkor mavzular:" if lang == "uz" else "📌 Тезкор мавзулар:", reply_markup=kb_faq_private())

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.from_user or not q.message:
        return
    data = q.data or ""
    await q.answer()

    user_id = q.from_user.id

    if data == "noop":
        return

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

    if data.startswith("menu:"):
        try:
            page = int(data.split(":", 1)[1])
        except Exception:
            page = 0
        lang = get_lang(user_id)
        await q.message.edit_text(
            "📚 Mavzular ro‘yxati:" if lang == "uz" else "📚 Мавзулар рўйхати:",
            reply_markup=kb_menu_paged(page, lang),
        )
        return

async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Groupda savol bo‘lsa:
    - bot o‘chiradi (huquqi bo‘lsa)
    - DMga deep-link tugmalar tashlaydi
    """
    if not update.effective_chat or not update.message or not update.effective_user:
        return
    chat = update.effective_chat
    if not chat_allowed(chat.id):
        return
    if chat.type not in ("group", "supergroup"):
        return

    text = (update.message.text or "").strip()
    norm = text.lower()

    # delete group message if possible
    try:
        await update.message.delete()
    except Exception:
        pass

    # if exact trigger matches, send direct deep link for that answer
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
        ])
        await chat.send_message("Savol shaxsiyda javoblanadi 👇", reply_markup=kb)
        return

    # default: show few topics as DM links
    await chat.send_message(
        "Savollar shaxsiyda (DM) javoblanadi. Quyidan mavzuni tanlang 👇",
        reply_markup=kb_faq_deeplink()
    )

# ----------------- MAIN -----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q. Railway Variables’ga BOT_TOKEN kiriting.")
    if not BOT_USERNAME:
        log.warning("BOT_USERNAME yo‘q. Deep-link ishlashi uchun BOT_USERNAME kiriting.")
    if not TRANSPORT_URL:
        log.warning("TRANSPORT_URL yo‘q. Promo ichida transport link chiqmaydi (lekin bot ishlaydi).")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))

    log.info("✅ Umra FAQ bot ishga tushdi | FAQs: %s | Allowed chat: %s | Username: %s",
             len(FAQ_DB), ALLOWED_CHAT_ID, BOT_USERNAME)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
