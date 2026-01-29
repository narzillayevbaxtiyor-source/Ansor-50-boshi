import os
import logging
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

# ================== ENV ==================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
MODEL = (os.getenv("MODEL") or "gpt-5.2").strip()

# Adminlar (vergul bilan)
ADMIN_IDS = set()
for x in (os.getenv("ADMIN_IDS") or "").split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_IDS.add(int(x))

# Kontaktlar
TAXI_CONTACT = (os.getenv("TAXI_CONTACT") or "").strip()
ALI_ATTAR_CONTACT = "@Ali_Attar0_bot"

PROMO_EVERY_N = int((os.getenv("PROMO_EVERY_N") or "3") or "3")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yo‘q")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY yo‘q")

# ================== LOG ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("ziyorat-umra-ai")

# ================== OPENAI ==================
client = OpenAI(api_key=OPENAI_API_KEY)

# ================== STATE ==================
STATE = {
    "taxi_enabled": True,
    "attar_enabled": True,
}

CHAT_MEMORY = {}
USER_MSG_COUNT = {}

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = f"""
SENING ROLING:
Sen “Ziyorat & Umra” bo‘yicha yordamchi AI botsan.
Javoblar o‘zbek tilida, muloyim va amaliy bo‘lsin.

JAVOB FORMAT:
1) ✅ Asosiy ma’lumot
2) 📖 Qiziqarli fakt
3) 🤲 Duo (mos bo‘lsa)
4) 🚕 / 🌿 Yumshoq tavsiya (faqat ruxsat bo‘lsa)

🚕 TAKSI:
Faqat transport mavzusida, majburlamasdan.
Kontakt: {TAXI_CONTACT}

🌿 ALI ATTAR:
Faqat safar/hadya mavzusida.
Ehromda atir ishlatmaslikni eslat.
Kontakt: {ALI_ATTAR_CONTACT}
"""

# ================== HELPERS ==================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def should_add_promo(user_id: int) -> bool:
    USER_MSG_COUNT[user_id] = USER_MSG_COUNT.get(user_id, 0) + 1
    return USER_MSG_COUNT[user_id] % PROMO_EVERY_N == 0

async def ask_ai(chat_id: int, user_id: int, text: str) -> str:
    history = CHAT_MEMORY.get(chat_id, [])[-10:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": text},
    ]

    resp = client.responses.create(
        model=MODEL,
        input=messages,
        temperature=0.7,
        max_output_tokens=700,
    )

    answer = resp.output_text.strip()

    # 🔌 Admin o‘chirganda reklama chiqmasin
    if not STATE["taxi_enabled"]:
        answer = answer.replace("🚕", "")
    if not STATE["attar_enabled"]:
        answer = answer.replace("🌿", "")

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": answer})
    CHAT_MEMORY[chat_id] = history

    return answer or "Kechirasiz, hozir javob bera olmadim."

# ================== ADMIN COMMANDS ==================
async def taxi_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    STATE["taxi_enabled"] = True
    await update.message.reply_text("✅ Taksi tavsiyalari YOQILDI")

async def taxi_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    STATE["taxi_enabled"] = False
    await update.message.reply_text("❌ Taksi tavsiyalari O‘CHIRILDI")

async def attar_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    STATE["attar_enabled"] = True
    await update.message.reply_text("✅ Ali Attar tavsiyalari YOQILDI")

async def attar_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    STATE["attar_enabled"] = False
    await update.message.reply_text("❌ Ali Attar tavsiyalari O‘CHIRILDI")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        f"📊 Holat:\n"
        f"🚕 Taksi: {'ON' if STATE['taxi_enabled'] else 'OFF'}\n"
        f"🌿 Ali Attar: {'ON' if STATE['attar_enabled'] else 'OFF'}"
    )

# ================== USER COMMANDS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕌 Ziyorat & Umra AI bot\n\n"
        "Savol bering:\n"
        "• Madinada 3 kunlik reja\n"
        "• Miyqotda nima qilinadi?\n"
        "• Ehromda nimalar mumkin emas?",
    )

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    await context.bot.send_chat_action(chat_id=msg.chat.id, action=ChatAction.TYPING)

    answer = await ask_ai(msg.chat.id, msg.from_user.id, msg.text)

    await msg.reply_text(answer, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Admin
    app.add_handler(CommandHandler("taxi_on", taxi_on))
    app.add_handler(CommandHandler("taxi_off", taxi_off))
    app.add_handler(CommandHandler("attar_on", attar_on))
    app.add_handler(CommandHandler("attar_off", attar_off))
    app.add_handler(CommandHandler("status", status_cmd))

    log.info("✅ Ziyorat & Umra AI bot (ADMIN PANEL bilan) ishga tushdi")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
