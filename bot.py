import os
import json
import logging
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from openai import AsyncOpenAI

# ----------------- ENV -----------------
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# ixtiyoriy: faqat bitta guruhda ishlasin (-100...)
ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID: Optional[int] = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

# ixtiyoriy: modelni env dan boshqarish
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()

STATE_FILE = "state.json"

# ----------------- LOG -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("umra_ai_bot")

# ----------------- STORAGE -----------------
DEFAULT_STATE: Dict[str, Any] = {
    "users": {},  # "user_id": {"lang": "uzb" or "kril"}
    "promo_enabled": True,
    "promo_text_uzb": (
        "🚖 Mashjid Nabaviydan Uhud tog‘iga (yoki boshqa ziyoratlarga) qulay borish uchun "
        "biz sizga arzon va ishonchli taksilarni topib beramiz.\n"
        "🌿 Ali Attar: uzoq saqlanadigan premium attarlar ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    "promo_text_kril": (
        "🚖 Машжид Набавийдан Уҳуд тоғига (ёки бошқа зиёратларга) қулай бориш учун "
        "биз сизга арзон ва ишончли таксиларни топиб берамиз.\n"
        "🌿 Ali Attar: узоқ сақланадиган премиум аттарлар ҳам бор. Алоқа: @Ali_Attar0_bot"
    ),
}

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return DEFAULT_STATE.copy()
        # merge defaults
        merged = DEFAULT_STATE.copy()
        merged.update(data)
        if "users" not in merged or not isinstance(merged["users"], dict):
            merged["users"] = {}
        return merged
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

def get_user_lang(user_id: int) -> str:
    u = STATE["users"].get(str(user_id), {})
    lang = (u.get("lang") or "uzb").lower()
    return "kril" if lang == "kril" else "uzb"

def set_user_lang(user_id: int, lang: str) -> None:
    lang = "kril" if lang == "kril" else "uzb"
    STATE["users"][str(user_id)] = {"lang": lang}
    save_state(STATE)

def promo_text(lang: str) -> str:
    if not STATE.get("promo_enabled", True):
        return ""
    return (STATE.get("promo_text_kril") if lang == "kril" else STATE.get("promo_text_uzb")) or ""

def inject_promo(answer: str, lang: str) -> str:
    p = promo_text(lang).strip()
    if not p:
        return answer
    return f"{answer}\n\n—\n{p}"

# ----------------- TEXTS -----------------
START_TEXT = {
    "uzb": (
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha yordamchi botman.\n\n"
        "Savol yozing yoki pastdagi tugmalardan birini bosing:"
    ),
    "kril": (
        "Ассалому алайкум! 🤍\n"
        "Мен Умра & Зиёрат бўйича ёрдамчи ботман.\n\n"
        "Савол ёзинг ёки пастдаги тугмалардан бирини босинг:"
    ),
}

SAMPLE_QUESTIONS = {
    "q1": {"uzb": "Madinaga keldim, 3 kunda qayerlarga boray?", "kril": "Мадинага келдим, 3 кунда қаерларга борай?"},
    "q2": {"uzb": "Miqotda nima qilinadi, qanday niyat?", "kril": "Миқотда нима қилинади, қандай ният?"},
    "q3": {"uzb": "Ehromda nimalar mumkin emas?", "kril": "Эҳромда нималар мумкин эмас?"},
}

def kb_start(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("UZB", callback_data="lang:uzb"),
            InlineKeyboardButton("КРИЛ", callback_data="lang:kril"),
        ],
        [InlineKeyboardButton(SAMPLE_QUESTIONS["q1"][lang], callback_data="ask:q1")],
        [InlineKeyboardButton(SAMPLE_QUESTIONS["q2"][lang], callback_data="ask:q2")],
        [InlineKeyboardButton(SAMPLE_QUESTIONS["q3"][lang], callback_data="ask:q3")],
    ])

# ----------------- OPENAI -----------------
SYSTEM_PROMPT_UZB = """
Siz “Ziyorat & Umra” bo‘limi uchun AI yordamchisiz.
Javob tili: o‘zbek (lotin).
6–14 band atrofida, aniq reja + odob + qisqa faktlar.
Fatvo bermang: zarur bo‘lsa “ishonchli ulamo/manba” deb eslating.
Javobning o‘rtasi yoki oxirida 1–2 qator yumshoq reklama bo‘lsin (taksi + Ali Attar), spamsiz.
""".strip()

SYSTEM_PROMPT_KRIL = """
Сиз “Зиёрат & Умра” бўлими учун AI ёрдамчисиз.
Жавоб тили: ўзбек (кирил).
6–14 банд атрофида, аниқ режа + одоб + қисқа фактлар.
Фатво берманг: зарур бўлса “ишончли уламо/манба” деб эслатинг.
Жавобнинг ўртаси ёки охирида 1–2 қатор юмшоқ реклама бўлсин (такси + Ali Attar), спамсиз.
""".strip()

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

async def ask_ai(user_text: str, lang: str) -> str:
    if not client:
        return "❗ OPENAI_API_KEY qo‘yilmagan." if lang == "uzb" else "❗ OPENAI_API_KEY қўйилмаган."

    system_prompt = SYSTEM_PROMPT_KRIL if lang == "kril" else SYSTEM_PROMPT_UZB

    try:
        resp = await client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
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
        if not text:
            return "Savolni boshqacha yozib ko‘ring." if lang == "uzb" else "Саволни бошқачароқ ёзиб кўринг."
        return text
    except Exception as e:
        log.exception("OpenAI error: %s", e)
        # aniqroq xabar
        return ("❗ AI ulanishida xatolik. Keyinroq urinib ko‘ring."
                if lang == "uzb"
                else "❗ AI уланишида хатолик. Кейинроқ уриниб кўринг.")

# ----------------- HANDLERS -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(START_TEXT[lang], reply_markup=kb_start(lang))

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()

    uid = q.from_user.id

    data = (q.data or "").strip()

    if data.startswith("lang:"):
        lang = data.split(":", 1)[1].strip()
        set_user_lang(uid, lang)
        lang = get_user_lang(uid)
        # start matnni qayta chiqaramiz
        try:
            await q.message.edit_text(START_TEXT[lang], reply_markup=kb_start(lang))
        except Exception:
            await q.message.reply_text(START_TEXT[lang], reply_markup=kb_start(lang))
        return

    if data.startswith("ask:"):
        key = data.split(":", 1)[1].strip()
        lang = get_user_lang(uid)
        user_text = SAMPLE_QUESTIONS.get(key, {}).get(lang)
        if not user_text:
            return

        try:
            await q.message.chat.send_action(ChatAction.TYPING)
        except Exception:
            pass

        answer = await ask_ai(user_text, lang)
        answer = inject_promo(answer, lang)
        await q.message.reply_text(answer)
        return

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    text = (update.message.text or "").strip()
    if not text:
        return
    if len(text) > 4000:
        text = text[:4000]

    lang = get_user_lang(update.effective_user.id)

    # Guruhda: o‘chirish + DMga javob
    if update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        try:
            await update.message.delete()
        except Exception:
            pass

        # DMga yuborish
        try:
            await context.bot.send_chat_action(chat_id=update.effective_user.id, action=ChatAction.TYPING)
        except Exception:
            pass

        answer = await ask_ai(text, lang)
        answer = inject_promo(answer, lang)

        try:
            await context.bot.send_message(chat_id=update.effective_user.id, text=answer)
        except Exception:
            # User botni /start qilmagan bo‘lishi mumkin
            pass
        return

    # Private: odatdagidek
    await update.effective_chat.send_action(ChatAction.TYPING)
    answer = await ask_ai(text, lang)
    answer = inject_promo(answer, lang)
    await update.message.reply_text(answer)

# ----------------- MAIN -----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q. Railway Variables’ga BOT_TOKEN qo‘ying.")

    if not OPENAI_API_KEY:
        log.warning("OPENAI_API_KEY yo‘q. Bot AI javob bera olmaydi.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_message))

    log.info("✅ Bot ishga tushdi | Allowed chat: %s | Model: %s", ALLOWED_CHAT_ID, OPENAI_MODEL)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
