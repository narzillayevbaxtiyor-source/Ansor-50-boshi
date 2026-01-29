import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

client = OpenAI(api_key=OPENAI_API_KEY)

# ================== LOG ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

# ================== PROMPT ==================
BASE_PROMPT = """
Siz Saudiya Arabistonida Umra va Ziyorat bo‘yicha AI yordamchisiz.

Siz:
- Madina va Makka ziyorat joylarini qiziqarli tarixiy voqealar bilan tushuntirasiz
- Miqot, ehrom, taqiqlar va duolarni sodda qilib aytasiz
- Javoblar yumshoq, muloyim va diniy hurmat bilan bo‘ladi

Javob o‘rtasida juda silliq tarzda quyidagicha tavsiya berasiz:
"Agar Masjid Nabaviy, Uhud tog‘i yoki Qubo masjidiga borishda qulay transport kerak bo‘lsa,
bizning ishonchli taksi xizmatimizdan foydalanishingiz mumkin."

Yana juda tabiiy tarzda:
"Ziyorat vaqtida toza va yoqimli hid muhim.
Ali Attar tomonidan tayyorlangan spirtsiz attarlar ziyorat uchun ayni muddao.
Aloqa: @Ali_Attar0_bot"

Hech qachon majburlamaysiz, faqat tavsiya qilasiz.
"""

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum 🌙\n\n"
        "Men Umra va Ziyorat bo‘yicha AI yordamchiman.\n"
        "Savolingizni yozing, men yordam beraman."
    )

async def ai_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BASE_PROMPT},
                {"role": "user", "content": user_text},
            ],
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)

    except Exception as e:
        log.exception("AI error")
        await update.message.reply_text("❗ Xatolik yuz berdi, keyinroq urinib ko‘ring.")

# ================== ADMIN ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    await update.message.reply_text(
        "🛠 Admin panel\n\n"
        "Hozircha sozlamalar statik.\n"
        "Keyingi bosqichda promptni shu yerdan o‘zgartiramiz."
    )

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, ai_answer))

    log.info("✅ AI Ziyorat bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
