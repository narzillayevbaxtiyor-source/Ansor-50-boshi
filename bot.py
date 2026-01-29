import os
import re
import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# OpenAI (Responses API)
from openai import OpenAI

# ================== ENV ==================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Model (default: gpt-5.2) - xohlasangiz Railway Variables'da MODEL ni o'zgartirasiz
MODEL = (os.getenv("MODEL") or "gpt-5.2").strip()

# Soft promo (taksi reklama jumlasi) - xohlasangiz o'zgartiring
TAXI_PROMO = (os.getenv("TAXI_PROMO") or
              "🚕 *Masjid Nabaviy → Uhud tog‘i* yoki *Madinadagi ziyorat joylari*ga borishda, "
              "arzon va ishonchli taksi topib beramiz. Istasangiz manzilingizni yozing — tezda mos haydovchi topamiz.")
TAXI_CONTACT = (os.getenv("TAXI_CONTACT") or "").strip()  # masalan: https://t.me/YourTaxiBot yoki @username

# Qanchadan keyin promo qo'shilsin (taxminan)
PROMO_EVERY_N = int((os.getenv("PROMO_EVERY_N") or "3").strip() or "3")

# Rate limit (bir user uchun)
COOLDOWN_SEC = int((os.getenv("COOLDOWN_SEC") or "2").strip() or "2")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Railway Variables ga BOT_TOKEN qo'ying.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY topilmadi. Railway Variables ga OPENAI_API_KEY qo'ying.")

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("ziyorat-umra-ai-bot")

# ================== OPENAI CLIENT ==================
client = OpenAI(api_key=OPENAI_API_KEY)

# ================== MEMORY (oddiy) ==================
# Eslatma: Railway restart bo'lsa memory yo'qoladi. Kerak bo'lsa keyin DB qo'shamiz.
CHAT_MEMORY = {}  # chat_id -> list[dict(role, content)]
USER_LAST_TS = {}  # user_id -> last request time
USER_MSG_COUNT = {}  # user_id -> count

SYSTEM_PROMPT = """
Siz "Ziyorat & Umra" bo‘yicha yordamchi AI botsiz (o‘zbek tilida).
Vazifangiz:
- Madina/Makka ziyorati va umra/ehrom/miyqot/duolar bo‘yicha foydali va qiziqarli ma’lumotlar berish.
- Javoblar aniq, xushmuomala, tartibli bo‘lsin: (1) qisqa reja, (2) amaliy tavsiyalar, (3) ehtiyot/fiqh eslatmasi.
- Fiqh masalalarida qat’iy hukm chiqarishga shoshilmang: "mazhabga ko‘ra farq qiladi" deb muloyim ayting,
  va zarur bo‘lsa "mahalliy imom/ustozdan tasdiqlang" de.
- Tibbiy/yuridik/taqiqlangan ishlar haqida xavfli ko‘rsatma bermang.
- Vaqt/joy bo‘yicha so‘ralsa: 3 kunlik, 5 kunlik, 1 kunlik marshrut (Madina/Makka) tuzib ber.
- Miyqotga borganda niyat/talbiya/duolarni eslat; ehromdagi man etilgan ishlar (parfyum, tirnoq/soch olish, ov, janjal) kabi umumiy qoidalarni ayt.
- Har 3-javobda (yoki kerakli joyda) juda yumshoq tarzda "taksi xizmatimiz"ni eslat: reklamani haddan oshirmang.
"""

def _clean_text(text: str) -> str:
    return (text or "").strip()

def _should_add_promo(user_id: int) -> bool:
    c = USER_MSG_COUNT.get(user_id, 0)
    return (c % PROMO_EVERY_N) == 0

def _promo_block() -> str:
    if TAXI_CONTACT:
        return f"\n\n{TAXI_PROMO}\n📩 Aloqa: {TAXI_CONTACT}"
    return f"\n\n{TAXI_PROMO}"

def _rate_limited(user_id: int) -> bool:
    import time
    now = time.time()
    last = USER_LAST_TS.get(user_id, 0)
    if now - last < COOLDOWN_SEC:
        return True
    USER_LAST_TS[user_id] = now
    return False

async def ask_ai(chat_id: int, user_id: int, user_text: str) -> str:
    # memory: oxirgi 10 ta turn
    mem = CHAT_MEMORY.get(chat_id, [])
    mem = mem[-10:]

    # promo qo'shish uchun hisob
    USER_MSG_COUNT[user_id] = USER_MSG_COUNT.get(user_id, 0) + 1

    # OpenAI Responses API (conversation state)
    # Manba: rasmiy Responses API misollari va conversation state qo'llanmasi. citeturn0search13turn0search15
    input_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *mem,
        {"role": "user", "content": user_text},
    ]

    # “promo” so'rovning o'ziga emas, javob oxiriga qo'shamiz (modelni chalg'itmaslik uchun).
    resp = client.responses.create(
        model=MODEL,
        input=input_messages,
        temperature=0.7,
        max_output_tokens=700,
    )

    # SDK javobidan matn olish (Responses API)
    out_text = ""
    try:
        out_text = resp.output_text or ""
    except Exception:
        # fallback: ehtiyot uchun
        out_text = str(resp)

    out_text = _clean_text(out_text)

    # promo qo'shish
    if _should_add_promo(user_id):
        out_text += _promo_block()

    # memory update
    mem.append({"role": "user", "content": user_text})
    mem.append({"role": "assistant", "content": out_text})
    CHAT_MEMORY[chat_id] = mem

    return out_text or "Kechirasiz, hozir javob chiqarmadim. Yana bir marta yozib ko‘ring."

# ================== COMMANDS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "Assalomu alaykum!\n\n"
        "Men *Ziyorat & Umra* bo‘yicha yordamchi botman.\n"
        "Savol bering:\n"
        "• “Madinada 3 kunlik ziyorat reja”\n"
        "• “Miyqotda qanday niyat qilinadi?”\n"
        "• “Ehromda nimalar mumkin emas?”\n",
        parse_mode=ParseMode.MARKDOWN,
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "Yordam:\n"
        "• Oddiy savol yuboring — men javob beraman.\n"
        "• “Madina 3 kun” / “Makka 2 kun” deb yozsangiz reja tuzib beraman.\n"
        "• Agar fiqh masalasi bo‘lsa, mazhablar farq qilishi mumkinligini ham aytaman.",
    )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or not update.effective_message:
        return
    CHAT_MEMORY.pop(chat.id, None)
    await update.effective_message.reply_text("✅ Suhbat xotirasi tozalandi. Endi yangidan boshlaymiz.")

# ================== MAIN TEXT HANDLER ==================
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    text = _clean_text(msg.text or "")
    if not text:
        return

    # oddiy anti-spam
    if _rate_limited(user.id):
        return

    try:
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
    except Exception:
        pass

    try:
        answer = await asyncio.to_thread(lambda: ask_ai(chat.id, user.id, text))
        # ask_ai async bo'lgani uchun to_thread kerak emas; lekin OpenAI call blok bo'lishi mumkin.
        # Shuning uchun quyida to'g'ridan-to'g'ri await qilamiz:
    except TypeError:
        # to_thread ichida coroutine bo'lib qoldi -> to'g'ri yo'l:
        answer = await ask_ai(chat.id, user.id, text)

    # Juda uzun bo'lsa bo'lib yuboramiz
    if len(answer) <= 3800:
        await msg.reply_text(answer, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        for chunk in [answer[i:i+3800] for i in range(0, len(answer), 3800)]:
            await msg.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))

    # Matnlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("✅ Ziyorat & Umra AI bot ishga tushdi. MODEL=%s", MODEL)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
