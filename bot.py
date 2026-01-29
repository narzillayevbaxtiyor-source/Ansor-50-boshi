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

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
RUNNER_TEXT = (os.getenv("RUNNER_TEXT") or "").strip()

# ================= LOG =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)

# ================= HELPERS =================
def with_runner(text: str) -> str:
    if not RUNNER_TEXT:
        return text
    return f"{text}\n\n{RUNNER_TEXT}"

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        with_runner(
            "Assalomu alaykum!\n\n"
            "Men ziyorat va umra bo‘yicha yordamchi botman.\n"
            "Savolingizni yozing."
        )
    )

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    # Hozircha AI o‘rniga demo javob
    answer = (
        "📍 Madinaga kelgan bo‘lsangiz, 3 kun ichida:\n"
        "1) Masjid Nabaviy\n"
        "2) Uhud tog‘i\n"
        "3) Qubo masjidi\n\n"
        "Bu joylarda Rasululloh ﷺ hayotlaridan muhim voqealar bo‘lgan."
    )

    await update.message.reply_text(with_runner(answer))

# ================= MAIN =================
def main():
    log.info("Bot ishga tushdi")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            ai_reply,
        )
    )

    app.run_polling()

if __name__ == "__main__":
    main()
