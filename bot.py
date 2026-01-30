# bot.py
# python-telegram-bot v20+ (polling)
# Vazifa:
# - 15 ta FAQ, 5 bet (har betda 8 ta tugma)
# - Tugma bosilganda: o‘sha xabarning ichida javob chiqadi + "⬅️ Orqaga" tugmasi
# - "Orqaga" bosilsa: o‘sha xabar qaytib menyuga (o‘sha betdagi tugmalar) chiqadi
# - Guruhda savol yozilsa: bot o‘chiradi va shaxsiyga menyuni yuboradi
# - Promo: faqat ayrim javoblarga chiqadi (xohlasangiz ro‘yxatini o‘zgartirasiz)

import os
import logging
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ----------------- ENV -----------------
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()

# Agar faqat bitta guruhda ishlasin desangiz: -100...
ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

# Deep-link ishlashi uchun bot username kerak bo'ladi (ixtiyoriy).
# Sizda bo'lmasa ham bot ishlaydi, faqat "savolni ustiga bosib botga ketish" deep-link bo'lmaydi.
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").strip()  # masalan: "Ali_Attar0_bot"

# Promo linklar
TRANSPORT_LINK = "https://t.me/saudia0dan_group/199"
ATTAR_LINK = "https://t.me/saudia0dan_group/20"
CONTACT_BOT = "@Ali_Attar0_bot"

# ----------------- LOG -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("umra_faq_bot")

# ----------------- FAQ DATA (15 ta) -----------------
# Har bir FAQ: {"uz": "...", "kr": "..."}.
# Birinchi qator tugma sarlavhasi sifatida olinadi.
FAQ: Dict[str, Dict[str, str]] = {
    "miqot": {
        "uz": (
            "🧭 Miqotda nima qilinadi?\n\n"
            "1) Miqotga yetmasdan oldin poklanish (g‘usl bo‘lsa — afzal).\n"
            "2) Ehrom kiyish (erkaklar: 2 mato; ayollar: odobli yopiq kiyim).\n"
            "3) Niyat: “Umra uchun ehromga kirdim” mazmunida.\n"
            "4) Talbiya: “Labbaykallohumma labbayk…”ni ko‘p aytish.\n"
            "5) Miqotdan ehromsiz o‘tib ketmaslik (zarurat bo‘lsa — ulamodan so‘rang).\n"
        ),
        "kr": (
            "🧭 Миқотда нима қилинади?\n\n"
            "1) Миқотга етмасдан олдин покланиш (ғусл бўлса — афзал).\n"
            "2) Эҳром кийиш (эркаклар: 2 мато; аёллар: одобли ёпиқ кийим).\n"
            "3) Ният: “Умра учун эҳромга кирдим” мазмунида.\n"
            "4) Талбия: “Лаббайкаллоҳумма лаббайк…”ни кўп айтиш.\n"
            "5) Миқотдан эҳромсиз ўтиб кетмаслик (зарурат бўлса — уламодан сўранг).\n"
        ),
    },
    "ehrom_taqiq": {
        "uz": (
            "🚫 Ehromdagi taqiqlar (qisqa)\n\n"
            "1) Atir/ifor surtish (ehromga kirgandan keyin) — mumkin emas.\n"
            "2) Soch/tirnoq olish — mumkin emas.\n"
            "3) Ov qilish (quruqlik hayvonlari) — mumkin emas.\n"
            "4) Jinsiy yaqinlik va shunga olib boruvchi ishlar — qat’iy man.\n"
            "5) Erkaklar: tikilgan kiyim (ko‘ylak, shim) va bosh yopish — man.\n"
            "6) Ayollar: yuzni niqob bilan berkitish va qo‘lqop — man.\n"
            "Eslatma: tafsilotlarda ulamo/manbaga tayaning.\n"
        ),
        "kr": (
            "🚫 Эҳромдаги тақиқлар (қисқа)\n\n"
            "1) Аттир/ифор суртиш (эҳромга киргандан кейин) — мумкин эмас.\n"
            "2) Соч/тирноқ олиш — мумкин эмас.\n"
            "3) Ов қилиш — мумкин эмас.\n"
            "4) Жинсий яқинлик ва шунга олиб борувчи ишлар — қатъий ман.\n"
            "5) Эркаклар: тик илган кийим ва бош ёпиш — ман.\n"
            "6) Аёллар: ниқоб ва қўлқоп — ман.\n"
            "Эслатма: тафсилотда уламога/манбага таянинг.\n"
        ),
    },
    "ehrom_niyat": {
        "uz": (
            "🧎 Ehrom niyati qanday qilinadi?\n\n"
            "1) Ehrom kiyib, miqotdan oldin tayyor bo‘lasiz.\n"
            "2) Qalbda niyat: “Umra uchun ehromga kirdim”.\n"
            "3) Talbiya aytasiz: “Labbaykallohumma labbayk…”.\n"
            "4) Shundan keyin ehrom qoidalari kuchga kiradi.\n"
        ),
        "kr": (
            "🧎 Эҳром нияти қандай қилинади?\n\n"
            "1) Эҳром кийиб, миқотдан олдин тайёр бўласиз.\n"
            "2) Қалбда ният: “Умра учун эҳромга кирдим”.\n"
            "3) Талбия айтасиз: “Лаббайкаллоҳумма лаббайк…”.\n"
            "4) Шундан кейин эҳром қоидалари кучга киради.\n"
        ),
    },
    "talbiya": {
        "uz": (
            "📿 Talbiya nima va qachon aytiladi?\n\n"
            "Talbiya — umra/hajning shiori.\n"
            "• Ehromga kirgandan keyin ko‘p aytiladi.\n"
            "• Makkaga yo‘lda, tavofga yaqinlashguncha davom etadi.\n"
            "• Ayollar ovozini baland qilmaydi.\n"
        ),
        "kr": (
            "📿 Талбия нима ва қачон айтилади?\n\n"
            "Талбия — умра/ҳажнинг шиори.\n"
            "• Эҳромга киргандан кейин кўп айтилади.\n"
            "• Маккага йўлда, тавофга яқинлашгунча давом этади.\n"
            "• Аёллар овозини баланд қилмайди.\n"
        ),
    },
    "umra_tartibi": {
        "uz": (
            "✅ Umraning qisqa tartibi\n\n"
            "1) Miqot → ehrom → niyat → talbiya.\n"
            "2) Makkaga kirib: Ka’bani ko‘rib duo.\n"
            "3) Tavof (7 aylanma).\n"
            "4) Sa’y (Safa–Marva 7 qatnov).\n"
            "5) Soch qisqartirish (erkaklar) / uchidan olish (ayollar).\n"
            "6) Ehromdan chiqish.\n"
        ),
        "kr": (
            "✅ Умранинг қисқа тартиби\n\n"
            "1) Миқот → эҳром → ният → талбия.\n"
            "2) Маккага кириб: Каъбани кўриб дуо.\n"
            "3) Тавоф (7 айланма).\n"
            "4) Са’й (Сафо–Марва 7 қатнов).\n"
            "5) Соч қисқартириш / учидан олиш.\n"
            "6) Эҳромдан чиқиш.\n"
        ),
    },
    "tavof_nima": {
        "uz": (
            "🕋 Tavof nima?\n\n"
            "Tavof — Ka’ba atrofida 7 marta aylanish.\n"
            "• Tahoratli bo‘lish afzal/zarur masalalarida fiqh farqlari bor.\n"
            "• O‘rtacha yurish, odamlarni itarmaslik.\n"
            "• Duo: o‘zingiz bilgan duolar, Qur’on oyatlari.\n"
        ),
        "kr": (
            "🕋 Тавоф нима?\n\n"
            "Тавоф — Каъба атрофида 7 марта айланиш.\n"
            "• Таҳорат масаласида мазҳаб/фиҳ фарқлари бор.\n"
            "• Одамларни итартмаслик.\n"
            "• Дуо: ўзингиз билган дуолар.\n"
        ),
    },
    "sa_y": {
        "uz": (
            "🏃 Sa’y nima?\n\n"
            "Sa’y — Safa va Marva orasida 7 qatnov.\n"
            "• Safadan boshlanadi, Marvada tugaydi.\n"
            "• Erkaklar yashil chiroqlar orasida yengil yuguradi (imkon bo‘lsa).\n"
            "• Duo: erkin.\n"
        ),
        "kr": (
            "🏃 Са’й нима?\n\n"
            "Са’й — Сафо ва Марва орасида 7 қатнов.\n"
            "• Сафодан бошланади, Марвада тугайди.\n"
            "• Эркаклар яшил чироқлар орасида енгил югуради.\n"
            "• Дуо: эркин.\n"
        ),
    },
    "soch_qirqish": {
        "uz": (
            "✂️ Umrada soch olish qanday?\n\n"
            "• Erkaklar: eng afzali — boshni qirish, yoki qisqartirish.\n"
            "• Ayollar: soch uchidan ozgina (odatda barmoq uchi miqdorida).\n"
            "• Shundan keyin ehromdan chiqiladi.\n"
        ),
        "kr": (
            "✂️ Умрада соч олиш қандай?\n\n"
            "• Эркаклар: афзали — бошни қириш, ёки қисқартириш.\n"
            "• Аёллар: соч учидан озгина.\n"
            "• Шундан кейин эҳромдан чиқилади.\n"
        ),
    },
    "madina_3kun": {
        "uz": (
            "🕌 Madinaga keldingizmi? 3 kunlik reja\n\n"
            "1-kun: Masjid Nabaviy (salom, Rawza navbati bo‘lsa).\n"
            "2-kun: Uhud (shuhadolar), Masjid Qiblatayn.\n"
            "3-kun: Qubo masjidi, jannatul baqi’ (tartib/vaqtga qarab).\n"
            "Eslatma: odob, sokinlik, jamoatga xalaqit bermaslik.\n"
        ),
        "kr": (
            "🕌 Мадинага келдингизми? 3 кунлик режа\n\n"
            "1-кун: Масжид Набавий (салом, Равза навбати бўлса).\n"
            "2-кун: Уҳуд (шуҳадолар), Қиблатайн масжиди.\n"
            "3-кун: Қубо масжиди, Жаннатул Бақи’.\n"
            "Эслатма: одоб, сокинлик.\n"
        ),
    },
    "rawza": {
        "uz": (
            "🌿 Rawza (Riyozul Janna) haqida\n\n"
            "• Rawza — Masjid Nabaviy ichidagi fazilatli joy.\n"
            "• Kirish tartibi ko‘pincha navbat/rezervga bog‘liq.\n"
            "• Ichkarida ko‘p turib qolmasdan, xushmuomala bo‘ling.\n"
        ),
        "kr": (
            "🌿 Равза (Риёзул Жанна) ҳақида\n\n"
            "• Равза — Масжид Набавий ичидаги фазилатли жой.\n"
            "• Кириш тартиби навбат/резервга боғлиқ.\n"
            "• Ичкарида одоб сақланади.\n"
        ),
    },
    "uhud": {
        "uz": (
            "⛰ Uhud tog‘i va saboq\n\n"
            "• Uhud — sahobalar sinovdan o‘tgan mashhur jang joyi.\n"
            "• Ziyorat: duolar, ibrat, tartib.\n"
            "• Shovqin-suron, tartibsizlikdan saqlaning.\n"
        ),
        "kr": (
            "⛰ Уҳуд тоғи ва сабоқ\n\n"
            "• Уҳуд — саҳобалар синовдан ўтган машҳур жанг жойи.\n"
            "• Зиёрат: дуолар, ибрат, тартиб.\n"
            "• Тартибсизликдан сақланинг.\n"
        ),
    },
    "qubo": {
        "uz": (
            "🕌 Qubo masjidi\n\n"
            "• Qubo — Madinadagi eng mashhur masjidlardan.\n"
            "• U yerda ikki rakat namozning fazilati zikr qilingan.\n"
            "• Borish-kelishda vaqtni to‘g‘ri rejalang.\n"
        ),
        "kr": (
            "🕌 Қубо масжиди\n\n"
            "• Қубо — Мадинадаги машҳур масжидлардан.\n"
            "• Икки ракат намоз фазилати зикр қилинган.\n"
            "• Бориш-келишни тўғри режалаш.\n"
        ),
    },
    "zamzam": {
        "uz": (
            "💧 Zamzam suvi odobi\n\n"
            "• Bismillah bilan ichish.\n"
            "• To‘yib ichish va duo qilish.\n"
            "• Isrof qilmaslik.\n"
        ),
        "kr": (
            "💧 Замзам суви одоби\n\n"
            "• Бисмиллаҳ билан ичиш.\n"
            "• Тўйиб ичиш ва дуо қилиш.\n"
            "• Исроф қилмаслик.\n"
        ),
    },
    "ramazon_umra": {
        "uz": (
            "🌙 Ramazonda umra\n\n"
            "• Juda gavjum bo‘ladi — xavfsizlik va sabr muhim.\n"
            "• Iftor/saharlik vaqtlarini oldindan rejalang.\n"
            "• Amallarda yengillik: odob va tartib.\n"
        ),
        "kr": (
            "🌙 Рамазонда умра\n\n"
            "• Жуда гавжум — хавфсизлик ва сабр муҳим.\n"
            "• Ифтор/саҳарликни олдиндан режалаш.\n"
            "• Одоб ва тартиб.\n"
        ),
    },
    "niyat": {
        "uz": (
            "🤍 Niyat haqida qisqa\n\n"
            "• Niyat — qalb ishi.\n"
            "• Til bilan aytish yordam beradi, lekin shart emas (fiqh farqlari bor).\n"
            "• Maqsad: Alloh roziligi.\n"
        ),
        "kr": (
            "🤍 Ният ҳақида қисқа\n\n"
            "• Ният — қалб иши.\n"
            "• Тил билан айтиш ёрдам беради (фиҳ фарқлари бор).\n"
            "• Мақсад: Аллоҳ розилиги.\n"
        ),
    },
}

TOP_FAQ_KEYS = [
    "miqot",
    "ehrom_taqiq",
    "ehrom_niyat",
    "talbiya",
    "umra_tartibi",
    "tavof_nima",
    "sa_y",
    "soch_qirqish",
    "madina_3kun",
    "rawza",
    "uhud",
    "qubo",
    "zamzam",
    "ramazon_umra",
    "niyat",
]

# 5 bet, har betda 8 ta tugma
ITEMS_PER_PAGE = 8
TOTAL_PAGES = 5  # user xohlaganidek

# Promo faqat ayrimlarida chiqsin
PROMO_KEYS = {"miqot", "madina_3kun", "uhud", "qubo"}

def chat_allowed(chat_id: int) -> bool:
    if ALLOWED_CHAT_ID is None:
        return True
    return chat_id == ALLOWED_CHAT_ID

def title_of(key: str, lang: str) -> str:
    txt = FAQ[key][lang].strip()
    return txt.split("\n", 1)[0].strip()

def promo_block(lang: str) -> str:
    if lang == "kr":
        return (
            "\n\n—\n"
            "🚖 Зиёрат жойларига қулай бориш учун арзон такси топиб берамиз.\n"
            f"🧭 Транспорт бўлими: {TRANSPORT_LINK}\n"
            "🌿 Ali Attar премиум аттарлари:\n"
            f"{ATTAR_LINK}\n"
            f"Алоқа: {CONTACT_BOT}"
        )
    return (
        "\n\n—\n"
        "🚖 Ziyorat joylariga qulay borish uchun arzon taksi topib beramiz.\n"
        f"🧭 Transport bo‘limi: {TRANSPORT_LINK}\n"
        "🌿 Ali Attar premium attarlari:\n"
        f"{ATTAR_LINK}\n"
        f"Aloqa: {CONTACT_BOT}"
    )

def build_faq_menu(page: int, lang: str) -> InlineKeyboardMarkup:
    page = max(0, min(TOTAL_PAGES - 1, page))
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    keys = TOP_FAQ_KEYS[start:end]

    rows = []
    for k in keys:
        # callback: faq:<key>:<lang>:<page>
        rows.append([InlineKeyboardButton(title_of(k, lang), callback_data=f"faq:{k}:{lang}:{page}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page:{page-1}:{lang}"))
    if page < TOTAL_PAGES - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page:{page+1}:{lang}"))
    if nav:
        rows.append(nav)

    # Tilni tez almashtirish (ixtiyoriy, yoqsa qoldiring)
    rows.append([
        InlineKeyboardButton("UZB", callback_data=f"lang:uz:{page}"),
        InlineKeyboardButton("КРИЛ", callback_data=f"lang:kr:{page}"),
    ])

    return InlineKeyboardMarkup(rows)

def build_answer_kb(lang: str, page: int) -> InlineKeyboardMarkup:
    # Orqaga: back:<lang>:<page>
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back:{lang}:{page}")]])

def start_text(lang: str) -> str:
    if lang == "kr":
        # Deep-link bo‘lsa: misol savolni bosganda botga ketishi
        if BOT_USERNAME:
            deep = f"https://t.me/{BOT_USERNAME}?start=faq_madina_3kun"
            example_line = f"• “Мадинага келдим, 3 кунда қаерларга борай?” ({deep})"
        else:
            example_line = "• “Мадинага келдим, 3 кунда қаерларга борай?”"

        return (
            "Ассалому алайкум! 🤍\n"
            "Мен Умра & Зиёрат бўйича ёрдамчиман.\n\n"
            "Қуйидаги саволлардан бирини танланг 👇\n"
            f"{example_line}"
        )
    else:
        if BOT_USERNAME:
            deep = f"https://t.me/{BOT_USERNAME}?start=faq_madina_3kun"
            example_line = f"• “Madinaga keldim, 3 kunda qayerlarga boray?” ({deep})"
        else:
            example_line = "• “Madinaga keldim, 3 kunda qayerlarga boray?”"

        return (
            "Assalomu alaykum! 🤍\n"
            "Men Umra & Ziyorat bo‘yicha yordamchiman.\n\n"
            "Quyidagi savollardan birini tanlang 👇\n"
            f"{example_line}"
        )

# ----------------- HANDLERS -----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    lang = "uz"
    await update.message.reply_text(
        start_text(lang),
        reply_markup=build_faq_menu(page=0, lang=lang)
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.message:
        return
    if not chat_allowed(q.message.chat.id):
        await q.answer()
        return

    data = (q.data or "").strip()
    await q.answer()

    # bet almashtirish
    if data.startswith("page:"):
        _, page_s, lang = data.split(":")
        page = int(page_s)
        await q.edit_message_reply_markup(reply_markup=build_faq_menu(page, lang))
        return

    # til almashtirish
    if data.startswith("lang:"):
        _, lang, page_s = data.split(":")
        page = int(page_s)
        # matnni ham yangilab qo'ysak (start matn o'sha xabarda tursa)
        # Lekin biz faqat tugmalarni almashtiramiz (yengilroq).
        await q.edit_message_reply_markup(reply_markup=build_faq_menu(page, lang))
        return

    # faq bosildi => o‘sha xabar ichida javob ko‘rsatamiz (edit text)
    if data.startswith("faq:"):
        _, key, lang, page_s = data.split(":")
        page = int(page_s)

        if key not in FAQ:
            await q.message.reply_text("Topilmadi.")
            return

        text = FAQ[key][lang].strip()
        if key in PROMO_KEYS:
            text += promo_block(lang)

        # XABARNI O'ZINING ICHIDA JAVOBGA O'ZGARTIRAMIZ + ORQAGA
        await q.edit_message_text(text=text, reply_markup=build_answer_kb(lang, page), disable_web_page_preview=True)
        return

    # orqaga => o‘sha xabarni menyuga qaytaramiz (o‘sha bet)
    if data.startswith("back:"):
        _, lang, page_s = data.split(":")
        page = int(page_s)

        # start matn + menu
        await q.edit_message_text(
            text=start_text(lang),
            reply_markup=build_faq_menu(page=page, lang=lang),
            disable_web_page_preview=True,
        )
        return

async def deep_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /start faq_madina_3kun kabi deep-link bo‘lsa, darhol shu javobni ko‘rsatadi
    # Telegram: https://t.me/<BOT_USERNAME>?start=faq_madina_3kun
    if not update.message:
        return

    args = context.args or []
    if not args:
        return await start_cmd(update, context)

    payload = args[0].strip()
    # format: faq_<key>
    if payload.startswith("faq_"):
        key = payload.replace("faq_", "", 1)
        lang = "uz"
        if key in FAQ:
            text = FAQ[key][lang].strip()
            if key in PROMO_KEYS:
                text += promo_block(lang)
            await update.message.reply_text(text, disable_web_page_preview=True)
            # keyin menyuni ham ko‘rsatib qo‘yamiz
            await update.message.reply_text(start_text(lang), reply_markup=build_faq_menu(0, lang))
            return

    # boshqacha payload bo'lsa oddiy start
    return await start_cmd(update, context)

async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Guruhda kim savol yozsa: o‘chiradi, shaxsiyga menyu yuboradi
    if not update.effective_chat or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    if update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        user = update.effective_user
        if not user:
            return

        # xabarni o‘chirish
        try:
            await update.message.delete()
        except Exception:
            pass

        # shaxsiyga yuborish
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=start_text("uz"),
                reply_markup=build_faq_menu(0, "uz"),
                disable_web_page_preview=True,
            )
        except Exception:
            # user botga /start bosmagan bo‘lishi mumkin
            pass

# ----------------- MAIN -----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q. Railway Variables ga BOT_TOKEN qo‘ying.")

    app = Application.builder().token(BOT_TOKEN).build()

    # /start (deep-link ham ishlasin)
    app.add_handler(CommandHandler("start", deep_start_cmd))

    # callback
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Guruhdagi oddiy textlarni ushlab qolamiz
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))

    log.info("✅ Umra FAQ bot ishga tushdi | Allowed chat: %s | BOT_USERNAME: %s", ALLOWED_CHAT_ID, BOT_USERNAME or "(yo‘q)")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
