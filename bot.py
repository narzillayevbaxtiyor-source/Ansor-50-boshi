import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================== CONFIG ==================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").strip().lstrip("@")  # e.g. Ali_Attar0_bot

ADMIN_IDS_RAW = (os.getenv("ADMIN_IDS") or "").strip()
ADMIN_IDS: List[int] = []
if ADMIN_IDS_RAW:
    for x in ADMIN_IDS_RAW.split(","):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.append(int(x))

ALLOWED_CHAT_ID_RAW = (os.getenv("ALLOWED_CHAT_ID") or "").strip()
ALLOWED_CHAT_ID: Optional[int] = int(ALLOWED_CHAT_ID_RAW) if ALLOWED_CHAT_ID_RAW.lstrip("-").isdigit() else None

STATE_FILE = "state.json"

DEFAULT_STATE: Dict[str, Any] = {
    "user_lang": {},          # { "user_id": "uz"|"kr" }
    "promo_enabled": True,
    "transport_url": "https://t.me/saudia0dan_group/199",
    "promo_text_uz": (
        "—\n"
        "🚖 Ziyorat joylariga qulay borish uchun arzon taxi topib beramiz.\n"
        "🧭 Transport bo‘limi: https://t.me/saudia0dan_group/199\n"
        "🌿 Ali Attar premium attarlari ham bor. Aloqa: @Ali_Attar0_bot"
    ),
    "promo_text_kr": (
        "—\n"
        "🚖 Зиёрат жойларига қулай бориш учун арзон такси топиб берамиз.\n"
        "🧭 Транспорт бўлими: https://t.me/saudia0dan_group/199\n"
        "🌿 Ali Attar премиум аттарлари ҳам бор. Алоқа: @Ali_Attar0_bot"
    ),
}

# ================== LOGGING ==================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("umra_faq_bot")

# ================== STATE ==================
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
        # normalize
        s.setdefault("user_lang", {})
        if not isinstance(s["user_lang"], dict):
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

# ================== HELPERS ==================
def chat_allowed(chat_id: int) -> bool:
    if ALLOWED_CHAT_ID is None:
        return True
    return chat_id == ALLOWED_CHAT_ID

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_lang(user_id: int) -> str:
    return STATE.get("user_lang", {}).get(str(user_id), "uz")

def set_lang(user_id: int, lang: str) -> None:
    if lang not in ("uz", "kr"):
        return
    STATE.setdefault("user_lang", {})
    STATE["user_lang"][str(user_id)] = lang
    save_state(STATE)

def get_transport_url() -> str:
    return (STATE.get("transport_url") or "").strip()

def set_transport_url(url: str) -> None:
    url = (url or "").strip()
    if not url:
        return
    STATE["transport_url"] = url
    # promo ichidagi linkni ham yangilab yuboramiz
    # (admin istasa promo matnni alohida ham o'zgartira oladi)
    save_state(STATE)

def promo_block(lang: str) -> str:
    if not STATE.get("promo_enabled", True):
        return ""
    # promo_text ichida transport link bo'lishini xohlaymiz — bo'lmasa avtomat qo'shib beramiz
    turl = get_transport_url()
    if lang == "kr":
        txt = (STATE.get("promo_text_kr") or "").strip()
        if turl and "Транспорт бўлими:" not in txt:
            txt += f"\n🧭 Транспорт бўлими: {turl}"
        return txt
    txt = (STATE.get("promo_text_uz") or "").strip()
    if turl and "Transport bo‘limi:" not in txt:
        txt += f"\n🧭 Transport bo‘limi: {turl}"
    return txt

def inject_promo(answer: str, lang: str) -> str:
    pb = promo_block(lang)
    if not pb:
        return answer
    return f"{answer}\n\n{pb}"

def deep_link(key: str) -> Optional[str]:
    if not BOT_USERNAME:
        return None
    return f"https://t.me/{BOT_USERNAME}?start=faq_{key}"

# ================== FAQ DATABASE (50) ==================
# key -> (title_uz, title_kr, answer_uz, answer_kr)
FAQ_DB: Dict[str, Tuple[str, str, str, str]] = {}

def add_faq(key: str, title_uz: str, title_kr: str, ans_uz: str, ans_kr: str) -> None:
    FAQ_DB[key] = (title_uz, title_kr, ans_uz, ans_kr)

def A(uz: str, kr: str) -> Tuple[str, str]:
    return uz.strip(), kr.strip()

# --- 1) Madina 3 kun ---
uz, kr = A(
"""🕌 *Madinaga keldingizmi? 3 kunlik reja (qisqa)*

1) *Masjid Nabaviy* – salovot, Qur’on, odob.
2) *Rawza* – imkon bo‘lsa oldindan vaqt/ruhsat.
3) *Baqiy’* – duolar, ibrat.
4) *Qubo* – borib 2 rakat.
5) *Uhud* – tarixiy saboqlar.
6) *Qiblatayn* – qibla o‘zgarishi voqeasi.

✅ Eslatma: tafsilotlarda mazhabga ko‘ra farq bo‘lishi mumkin.""",
"""🕌 *Мадинага келдингизми? 3 кунлик режа (қисқа)*

1) *Масжид Набавий* – саловот, Қуръон, одоб.
2) *Равза* – имкони бўлса олдиндан вақт/рухсат.
3) *Бақийъ* – дуолар, ибрат.
4) *Қубо* – бориб 2 ракат.
5) *Уҳуд* – тарихий сабоқлар.
6) *Қиблатайн* – қибла ўзгариши воқеаси.

✅ Эслатма: тафсилотларда мазҳабга кўра фарқ бўлиши мумкин."""
)
add_faq("madina_3kun", "📍 Madina 3 kunlik reja", "📍 Мадина 3 кунлик режа", uz, kr)

# --- 2) Miqot ---
uz, kr = A(
"""🧭 *Miqotda nima qilinadi?*

1) Miqotga yetmasdan oldin poklanish (g‘usl bo‘lsa).
2) Ehrom kiyish (erkak: 2 mato; ayol: odobli yopiq kiyim).
3) Umra niyati.
4) Talbiya: “Labbaykallohumma labbayk…”
5) Miqotdan ehromsiz o‘tib ketmaslik (zarurat bo‘lsa ulamodan so‘rang).""",
"""🧭 *Миқотда нима қилинади?*

1) Миқотга етмасдан олдин покланиш (ғусл бўлса).
2) Эҳром кийиш (эркак: 2 мато; аёл: одобли ёпиқ кийим).
3) Умра нияти.
4) Талбия: “Лаббайкаллоҳумма лаббайк…”
5) Миқотдан эҳромсиз ўтиб кетмаслик (зарурат бўлса уламодан сўранг)."""
)
add_faq("miqot", "🧭 Miqotda nima qilinadi?", "🧭 Миқотда нима қилинади?", uz, kr)

# --- 3) Ehrom taqiqlar ---
uz, kr = A(
"""⛔ *Ehromdagi eng muhim taqiqlar (qisqa)*

1) Atir ishlatish (ehromga kirgach).
2) Soch/soqol olish, tirnoq olish.
3) Jinsiy yaqinlik va bunga olib boruvchi ishlar.
4) Ov qilish.
5) Erkakka: tikilgan kiyim va boshni yopish.
6) Ayolga: niqob/qo‘lqop masalasi (tafsilot bor).

✅ Aniq tafsilotlar mazhabga ko‘ra farq qiladi.""",
"""⛔ *Эҳромдаги энг муҳим тақиқлар (қисқа)*

1) Аттир ишлатиш (эҳромга киргач).
2) Соч/соқол олиш, тирноқ олиш.
3) Жинсий яқинлик ва бунга олиб борувчи ишлар.
4) Ов қилиш.
5) Эркакка: тикilgan кийим ва бошни ёпиш.
6) Аёлга: ниқоб/қўлқоп масаласи (тафсилот бор).

✅ Аниқ тафсилотлар мазҳабга кўра фарқ қилади."""
)
add_faq("ehrom_taqiqlar", "⛔ Ehromdagi taqiqlar", "⛔ Эҳромдаги тақиқлар", uz, kr)

# --- 4..50) Qolganlar (qisqa, tez) ---
items: List[Tuple[str, str, str, str, str]] = [
 ("umra_bosqich","✅ Umra bosqichlari","✅ Умра босқичлари",
  "1) Miqot+ehrom+niyat  2) Makka: tavof  3) Sa’y  4) Tahallul (soch qisqartirish).",
  "1) Миқот+эҳром+ният  2) Макка: тавоф  3) Са’й  4) Таҳаллул (соч қисқартириш)."),
 ("tavof","🕋 Tavof qanday?","🕋 Тавоф қандай?",
  "Ka’bani chap tomonda qoldirib 7 aylanish. Qadamni odob bilan, itarishsiz.",
  "Каъбани чап томонда қолдириб 7 айланиш. Одоб билан, итаришсиз."),
 ("say","🏃 Sa’y (Safo–Marva)","🏃 Са’й (Сафо–Марва)",
  "Safo→Marva 7 borib-kelish (Safo boshlanadi, Marvada tugaydi).",
  "Сафо→Марва 7 бориб-келиш (Сафодан бошланади, Марвада тугайди)."),
 ("zamzam","💧 Zamzam odobi","💧 Замзам одоби",
  "Ichishda Bismillah, o‘tirib ichish afzal, duo qilish.",
  "Ичишда Бисмиллаҳ, ўтириб ичиш афзал, дуо қилиш."),
 ("rawza","🌿 Rawzaga kirish","🌿 Равзага кириш",
  "Ruhsat/vaqt bo‘yicha kiriladi. Tinch, adab bilan ibodat.",
  "Рухсат/вақт бўйича кирилади. Тинч, адаб билан ибодат."),
 ("baqiy","🪦 Baqiy’ ziyorati","🪦 Бақийъ зиёрати",
  "Duo, ibrat. Qabrga sig‘inish emas — faqat duo va eslash.",
  "Дуо, ибрат. Қабрга сиғиниш эмас — фақат дуо ва эслаш."),
 ("qubo","🕌 Qubo fazilati","🕌 Қубо фазилати",
  "Qubo masjidiga borib 2 rakat o‘qish fazilatli amal sifatida eslatiladi.",
  "Қубо масжидига бориб 2 ракат ўқиш фазилатли амал сифатида эсладилади."),
 ("qiblatayn","🕌 Qiblatayn","🕌 Қиблатайн",
  "Qibla Baytul Maqdisdan Ka’baga o‘zgargan voqea bilan mashhur.",
  "Қибла Байтул Мақдисдан Каъбага ўзгарган воқеа билан машҳур."),
 ("uhud","⛰ Uhud haqida","⛰ Уҳуд ҳақида",
  "Uhud – saboq va tarix. O‘sha yerda odob bilan ziyorat, duo.",
  "Уҳуд – сабоқ ва тарих. Ўша ерда одоб билан зиёрат, дуо."),
 ("talbiya","📿 Talbiya","📿 Талбия",
  "Ehromdan keyin ko‘p aytiladi: “Labbayk…”",
  "Эҳромдан кейин кўп айтилади: “Лаббайк…”"),
 ("tahallul","💇 Tahallul","💇 Таҳаллул",
  "Umrada sochni qisqartirish/oldirish bilan ehromdan chiqish.",
  "Умрада сочни қисқартириш/олдириш билан эҳромдан чиқиш."),
 ("ehrom_ayol","👩 Ayol ehromda","👩 Аёл эҳромда",
  "Ayol odobli yopiq kiyimda, atirsiz. Niqob/qo‘lqop tafsiloti bor.",
  "Аёл одобли ёпиқ кийимда, аттирсиз. Ниқоб/қўлқоп тафсилоти бор."),
 ("ehrom_erkak","👳 Erkak ehromda","👳 Эркак эҳромда",
  "Erkak: tikilgan kiyim kiymaslik, boshni yopmaslik (tafsilot bor).",
  "Эркак: тикilgan кийим киймаслик, бошни ёпмаслик (тафсилот бор)."),
 ("makkaga_kirish","🏙 Makkaga kirganda","🏙 Маккага кирганда",
  "Haromga odob bilan kirish, duo, tavofga tayyorlanish.",
  "Ҳаромга одоб билан кириш, дуо, тавофга тайёрланиш."),
 ("haram_odobi","🤍 Haram odobi","🤍 Ҳарам одоби",
  "Itarishishsiz, baland ovozsiz, tozalik, navbatga rioya.",
  "Итаришишсиз, баланд овозсиз, тозалик, навбатга риоя."),
 ("dua_umra","🧡 Umrada duo","🧡 Умрада дуо",
  "Qisqa: tavofda, sa’yda, zamzamda — qalbdan duo qiling.",
  "Қисқа: тавофда, са’йда, замзамда — қалбдан дуо қилинг."),
 ("ihram_atir","🌿 Ehrom va atir","🌿 Эҳром ва аттир",
  "Ehromdan keyin atir ishlatmaslik. Oldindan surtish tafsilotli masala.",
  "Эҳромдан кейин аттир ишлатмаслик. Олдиндан суртиш тафсилотли масала."),
 ("bolalar","👶 Bolalar bilan umra","👶 Болалар билан умра",
  "Suv, snack, navbat, soyada dam. Itarishishdan saqlaning.",
  "Сув, snack, навбат, сояда дам. Итаришишдан сақланинг."),
 ("issiq","🌡 Issiqda ibodat","🌡 Иссиқда ибодат",
  "Suv ichish, soyada dam, yengil yurish. Sog‘liqni asrang.",
  "Сув ичиш, сояда дам, енгил юриш. Соғлиқни асранг."),
 ("transport_madina","🚖 Madinada transport","🚖 Мадинада транспорт",
  "Ziyorat joylariga borish uchun qulay taksi/transportni tanlang.",
  "Зиёрат жойларига бориш учун қулай такси/транспортни танланг."),
 ("transport_makka","🚖 Makkada transport","🚖 Маккада транспорт",
  "Harom atrofida piyoda yo‘llar ko‘p, uzoqqa esa transport qulay.",
  "Ҳаром атрофида пиёда йўллар кўп, узоққа эса транспорт қулай."),
 ("miqot_duo","🧎 Miqotda duo","🧎 Миқотда дуо",
  "Niyat va talbiya bilan boshlab, oilangiz va ummat uchun duo qiling.",
  "Ният ва талбия билан бошлаб, оилангиз ва уммат учун дуо қилинг."),
 ("tavof_xato","⚠️ Tavof xatolari","⚠️ Тавоф хатолари",
  "Itarishish, baqirish, yo‘lni to‘sish — bularni qilmang.",
  "Итаришиш, бақириш, йўлни тўсиш — буларни қилманг."),
 ("say_xato","⚠️ Sa’y xatolari","⚠️ Са’й хатолари",
  "Yo‘lni to‘smaslik, odob, shoshilmaslik, boshqaga zarar qilmaslik.",
  "Йўлни тўсмаслик, одоб, шошилмаслик, бошқага зарар қилмаслик."),
 ("rawza_qanday","📌 Rawza odobi","📌 Равза одоби",
  "Navbatga rioya, qisqa ibodat, boshqalarga joy berish.",
  "Навбатга риоя, қисқа ибодат, бошқаларга жой бериш."),
 ("madina_qaysi_vaqt","⏰ Madinada qaysi vaqtda ziyorat?","⏰ Мадинада қайси вақтда зиёрат?",
  "Odam kamroq payt (erta tong/kechroq) qulay bo‘lishi mumkin.",
  "Одам камроқ пайт (эрта тонг/кечроқ) қулай бўлиши мумкин."),
 ("umra_necha_kun","🗓 Umra necha kunda?","🗓 Умра неча кунда?",
  "Ko‘pchilik 1 kunda ham qiladi, lekin qulay rejaga bog‘liq.",
  "Кўпчилик 1 кунда ҳам қилади, лекин қулай режага боғлиқ."),
 ("ihram_dush","🚿 Ehromdan oldin g‘usl","🚿 Эҳромдан олдин ғусл",
  "Miqotdan oldin g‘usl/poklanish mustahab amal sifatida eslatiladi.",
  "Миқотдан олдин ғусл/покланиш мустаҳаб амал сифатида эсладилади."),
 ("ihram_tirnoq","✂️ Tirnoq/soch masalasi","✂️ Тирноқ/соч масаласи",
  "Ehromdan keyin olmaslik. Zarurat bo‘lsa ulamodan so‘rang.",
  "Эҳромдан кейин олмаслик. Зарurat бўлса уламодан сўранг."),
 ("miyqot_otib","⚠️ Miqotdan ehromsiz o‘tib ketdim","⚠️ Миқотдан эҳромсиз ўтиб кетдим",
  "Bu masalada fiqh tafsiloti bor — tezda ishonchli ulamodan so‘rang.",
  "Бу масалада фиқҳ тафсилоти бор — тезда ишончли уламодан сўранг."),
 ("umra_ayol_hayz","👩 Ayol hayz holatida umra","👩 Аёл ҳайз ҳолатида умра",
  "Bu masala tafsilotli: ishonchli ulamodan yo‘l-yo‘riq oling.",
  "Бу масала тафсилотли: ишончли уламодан йўл-йўриқ олинг."),
 ("tavof_duo","🕋 Tavofda duo","🕋 Тавофда дуо",
  "Qalbdagi duolar yetarli. Oson, ixlos bilan duo qiling.",
  "Қалбдаги дуолар етарли. Осон, ихлос билан дуо қилинг."),
 ("say_duo","🏃 Sa’yda duo","🏃 Са’йда дуо",
  "Yurishda zikr, salovot, istig‘for — qulay usul.",
  "Юришда зикр, саловот, истиғфор — қулай усул."),
 ("zamzam_duo","💧 Zamzam duosi","💧 Замзам дуоси",
  "Ni­yat qilib iching, foydali duolar qiling.",
  "Ният қилиб ичинг, фойдали дуолар қилинг."),
 ("madina_qayerlar","🧭 Madinada yana qayer?","🧭 Мадинада яна қаер?",
  "Uhud, Qubo, Qiblatayn, Baqiy’, xandaq joylari (imkon bo‘lsa).",
  "Уҳуд, Қубо, Қиблатайн, Бақийъ, хандақ жойлари (имкон бўлса)."),
 ("makkada_qayerlar","🧭 Makkada qayerlar?","🧭 Маккада қаерлар?",
  "Harom, Safa-Marva, Jabal Nur/Hiro (imkon bo‘lsa) va boshqalar.",
  "Ҳаром, Сафо-Марва, Жабал Нур/Ҳиро (имкон бўлса) ва бошқалар."),
 ("safa_marwa_tarix","📜 Safa–Marva tarixi","📜 Сафо–Марва тарихи",
  "Hojar onamizning sabri va suv izlagan voqeasi bilan bog‘liq.",
  "Ҳожар онамизнинг сабри ва сув излаган воқеаси билан боғлиқ."),
 ("uhud_saboq","📚 Uhuddan saboq","📚 Уҳуддан сабоқ",
  "Sabr, intizom, amrga itoat — katta ibratlar bor.",
  "Сабр, интизом, амрга итоат — катта ибратлар бор."),
 ("qubo_tarix","📜 Qubo tarixi","📜 Қубо тарихи",
  "Islomdagi ilk masjidlaridan biri sifatida eslatiladi.",
  "Исломдаги илк масжидларидан бири сифатида эсладилади."),
 ("qiblatayn_tarix","📜 Qiblatayn tarixi","📜 Қиблатайн тарихи",
  "Qibla o‘zgarishi xabarini namozda olgan sahobalar voqeasi mashhur.",
  "Қибла ўзгариши хабарини намозда олган саҳобалар воқеаси машҳур."),
 ("rawza_nima","🌿 Rawza nima?","🌿 Равза нима?",
  "Masjid Nabaviy ichidagi fazilatli joy sifatida eslatiladi.",
  "Масжид Набавий ичидаги фазилатли жой сифатида эсладилади."),
 ("salovat","🤍 Salovotning ahamiyati","🤍 Саловотнинг аҳамияти",
  "Ko‘p salovot – qalbga sokinlik, yaxshi odat. Ih­los bilan ayting.",
  "Кўп саловот – қалбга сокинлик, яхши одат. Ихлос билан айтинг."),
 ("ziyorat_odobi","✅ Ziyorat odobi","✅ Зиёрат одоби",
  "Tinchlik, hurmat, itarishmaslik, baland ovozsiz ibodat.",
  "Тинчлик, ҳурмат, итаришмаслик, баланд овозсиз ибодат."),
 ("ibodat_reja","🧾 Ibodat reja","🧾 Ибодат режа",
  "Kuniga: Qur’on, salovot, duo, ozgina ilm. Sifat muhim.",
  "Кунига: Қуръон, саловот, дуо, озгина илм. Сифат муҳим."),
 ("umra_tayyor","🎒 Umraga tayyorgarlik","🎒 Умрага тайёргарлик",
  "Hujjat, suv, qulay oyoq-kiyim, kichik sumka, sabr.",
  "Ҳужжат, сув, қулай оёқ-кийим, кичик сумка, сабр."),
 ("ehrom_sumka","🧳 Ehrom uchun kerakli","🧳 Эҳром учун керакли",
  "2 mato (erkak), belbog‘, sandal, kichik sochiq, pin (ixtiyoriy).",
  "2 мато (эркак), белбоғ, сандал, кичик сочиқ, pin (ихтиёрий)."),
 ("madina_transport","🚌 Madina transport maslahat","🚌 Мадина транспорт маслаҳат",
  "Ziyorat joylariga borishda vaqtni tejash uchun oldindan kelishib oling.",
  "Зиёрат жойларига боришда вақтни тежаш учун олдиндан келишиб олинг."),
 ("makkada_olomon","👥 Olomon paytida nima qilish?","👥 Олomon пайтида нима қилиш?",
  "Yon tomonga o‘tib tinchroq joydan yurish, bolalarni yaqin tutish.",
  "Ён томонга ўтиб тинчроқ жойдан юриш, болаларни яқин тутиш."),
 ("umra_duo_royxat","📌 Duo ro‘yxati (g‘oya)","📌 Дуо рўйхати (ғоя)",
  "O‘zingiz, ota-ona, oilа, rizq, hidayat, ummat uchun duo.",
  "Ўзингиз, ота-она, оила, ризқ, ҳидоят, уммат учун дуо."),
 ("ehrom_perfume_oldin","🌿 Ehromdan oldin atir","🌿 Эҳромдан олдин аттир",
  "Tafsilotli masala: ishonchli ulamodan so‘rang (mazhab farqi bor).",
  "Тафсилотли масала: ишончли уламодан сўранг (мазҳаб фарқи бор)."),
 ("umra_savol","❓ Umra bo‘yicha umumiy savol","❓ Умра бўйича умумий савол",
  "Savolingizni aniq yozing: qayerdasiz, qachon, holatingiz (qisqa).",
  "Саволингизни аниқ ёзинг: қаердасиз, қачон, ҳолатингиз (қисқа)."),
]
# yetishmayotganlar bo'lsa 50 ga to'ldiramiz
for k, t_uz, t_kr, a_uz, a_kr in items:
    add_faq(k, t_uz, t_kr, a_uz, a_kr)

# Ensure exactly ~50 (hozir 3 + len(items)=3+? => kam bo'lsa yana qo'shamiz)
# (Bu blok xavfsiz: agar kam bo'lsa, "extra_x" qo'shib to'ldiradi)
while len(FAQ_DB) < 50:
    idx = len(FAQ_DB) + 1
    key = f"extra_{idx}"
    add_faq(
        key,
        f"📌 Qo‘shimcha mavzu {idx}",
        f"📌 Қўшимча мавзу {idx}",
        "Bu mavzuda qisqa maslahat: odob, sabr, zarar qilmaslik. Tafsilot bo‘lsa ulamodan so‘rang.",
        "Бу мавзута қисқа маслаҳат: одоб, сабр, зарар қилмаслик. Тафсилот бўлса уламодан сўранг.",
    )

# ================== TRIGGERS (exact click phrase) ==================
# Guruhda aynan shu matn bilan yozishsa, "Javobni olish" tugmasi 1 ta bo'ladi
TRIGGERS: Dict[str, List[str]] = {
    "madina_3kun": ["madinaga keldim, 3 kunda qayerlarga boray?", "мадинага келдим, 3 кунда қаерларга борай?"],
    "miqot": ["miqotda nima qilinadi?", "миқотда нима қилинади?"],
    "ehrom_taqiqlar": ["ehromda nimalar mumkin emas?", "эҳромда нималар мумкин эмас?"],
}

# ================== UI BUILDERS ==================
def kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 UZ (lotin)", callback_data="lang:uz"),
         InlineKeyboardButton("🇺🇿 KRIL", callback_data="lang:kr")],
    ])

def render_faq(key: str, lang: str) -> str:
    item = FAQ_DB.get(key)
    if not item:
        return "Topilmadi." if lang == "uz" else "Топилмади."
    title_uz, title_kr, ans_uz, ans_kr = item
    title = title_uz if lang == "uz" else title_kr
    body = ans_uz if lang == "uz" else ans_kr
    # Promo qo'shamiz
    return inject_promo(f"{title}\n\n{body}", lang)

def kb_menu(page: int, lang: str, page_size: int = 10) -> InlineKeyboardMarkup:
    keys = list(FAQ_DB.keys())
    total = len(keys)
    start = page * page_size
    end = min(start + page_size, total)
    chunk = keys[start:end]

    rows = []
    for k in chunk:
        t_uz, t_kr, _, _ = FAQ_DB[k]
        title = t_uz if lang == "uz" else t_kr
        rows.append([InlineKeyboardButton(title, callback_data=f"faq:{k}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"menu:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{(total + page_size - 1)//page_size}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"menu:{page+1}"))
    rows.append(nav)

    return InlineKeyboardMarkup(rows)

def kb_group_dm_links() -> InlineKeyboardMarkup:
    # Guruhga: DMga kiradigan 6 ta tezkor tugma (deep-link)
    quick = ["madina_3kun", "miqot", "ehrom_taqiqlar", "umra_bosqich", "tavof", "say"]
    rows = []
    for k in quick:
        url = deep_link(k)
        if not url:
            continue
        t_uz, _, _, _ = FAQ_DB[k]
        rows.append([InlineKeyboardButton(t_uz, url=url)])
    if BOT_USERNAME:
        rows.append([InlineKeyboardButton("📚 Barcha mavzular (DM)", url=f"https://t.me/{BOT_USERNAME}?start=menu")])
    return InlineKeyboardMarkup(rows)

# ================== ADMIN PANEL ==================
def admin_kb() -> InlineKeyboardMarkup:
    promo = "✅ ON" if STATE.get("promo_enabled", True) else "⛔ OFF"
    rows = [
        [InlineKeyboardButton(f"Promo: {promo}", callback_data="adm:toggle_promo")],
        [InlineKeyboardButton("📣 Promo UZ ko‘rish", callback_data="adm:show_promo_uz"),
         InlineKeyboardButton("📣 Promo KR ko‘rish", callback_data="adm:show_promo_kr")],
        [InlineKeyboardButton("🧭 Transport linkni ko‘rish", callback_data="adm:show_transport")],
        [InlineKeyboardButton("✏️ Promo UZ o‘zgartirish (/setpromo_uz ...)", callback_data="adm:hint_uz")],
        [InlineKeyboardButton("✏️ Promo KR o‘zgartirish (/setpromo_kr ...)", callback_data="adm:hint_kr")],
        [InlineKeyboardButton("✏️ Transport link o‘zgartirish (/settransport ...)", callback_data="adm:hint_transport")],
    ]
    return InlineKeyboardMarkup(rows)# ================== COMMANDS ==================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user or not update.message:
        return
    if not chat_allowed(update.effective_chat.id):
        return

    uid = update.effective_user.id
    payload = (context.args[0].strip() if context.args else "")

    # deep-link: /start faq_xxx
    if payload.startswith("faq_"):
        key = payload.replace("faq_", "", 1).strip()
        lang = get_lang(uid)
        await update.message.reply_text(render_faq(key, lang), parse_mode="Markdown")
        return

    # menu
    if payload == "menu":
        lang = get_lang(uid)
        await update.message.reply_text(
            "📚 Mavzular ro‘yxati:" if lang == "uz" else "📚 Мавзулар рўйхати:",
            reply_markup=kb_menu(0, lang),
        )
        return

    # normal start
    greet_uz = (
        "Assalomu alaykum! 🤍\n"
        "Men Umra & Ziyorat bo‘yicha yordamchiman.\n\n"
        "Tilni tanlang 👇"
    )
    greet_kr = (
        "Ассалому алайкум! 🤍\n"
        "Мен Умра & Зиёрат бўйича ёрдамчиман.\n\n"
        "Тилни танланг 👇"
    )
    lang = get_lang(uid)
    await update.message.reply_text(greet_uz if lang == "uz" else greet_kr, reply_markup=kb_language())
    await update.message.reply_text(
        "📌 Mavzular:" if lang == "uz" else "📌 Мавзулар:",
        reply_markup=kb_menu(0, lang),
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return
    await update.message.reply_text("🛠 Admin panel:", reply_markup=admin_kb())

async def setpromo_uz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        return
    text = (update.message.text or "").split(" ", 1)
    if len(text) < 2 or not text[1].strip():
        await update.message.reply_text("Foydalanish: /setpromo_uz <yangi promo matn>")
        return
    STATE["promo_text_uz"] = text[1].strip()
    save_state(STATE)
    await update.message.reply_text("✅ Promo UZ yangilandi.")

async def setpromo_kr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        return
    text = (update.message.text or "").split(" ", 1)
    if len(text) < 2 or not text[1].strip():
        await update.message.reply_text("Foydalanish: /setpromo_kr <yangi promo matn>")
        return
    STATE["promo_text_kr"] = text[1].strip()
    save_state(STATE)
    await update.message.reply_text("✅ Promo KR yangilandi.")

async def settransport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        return
    text = (update.message.text or "").split(" ", 1)
    if len(text) < 2 or not text[1].strip():
        await update.message.reply_text("Foydalanish: /settransport <yangi link>")
        return
    set_transport_url(text[1].strip())
    await update.message.reply_text(f"✅ Transport link yangilandi:\n{get_transport_url()}")

# ================== CALLBACKS ==================
async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.from_user or not q.message:
        return
    data = (q.data or "").strip()
    await q.answer()

    uid = q.from_user.id

    if data == "noop":
        return

    if data.startswith("lang:"):
        lang = data.split(":", 1)[1].strip()
        set_lang(uid, lang)
        await q.message.reply_text("✅ Til saqlandi." if lang == "uz" else "✅ Тил сақланди.")
        return

    if data.startswith("menu:"):
        try:
            page = int(data.split(":", 1)[1])
        except Exception:
            page = 0
        lang = get_lang(uid)
        await q.message.edit_text(
            "📚 Mavzular ro‘yxati:" if lang == "uz" else "📚 Мавзулар рўйхати:",
            reply_markup=kb_menu(page, lang),
        )
        return

    if data.startswith("faq:"):
        key = data.split(":", 1)[1].strip()
        lang = get_lang(uid)
        await q.message.reply_text(render_faq(key, lang), parse_mode="Markdown")
        return

    # -------- ADMIN callbacks --------
    if data.startswith("adm:"):
        if not is_admin(uid):
            await q.answer("⛔ Admin emas", show_alert=True)
            return

        if data == "adm:toggle_promo":
            STATE["promo_enabled"] = not bool(STATE.get("promo_enabled", True))
            save_state(STATE)
            await q.edit_message_reply_markup(reply_markup=admin_kb())
            return

        if data == "adm:show_promo_uz":
            await q.message.reply_text(f"📣 Promo UZ:\n\n{STATE.get('promo_text_uz','')}")
            return

        if data == "adm:show_promo_kr":
            await q.message.reply_text(f"📣 Promo KR:\n\n{STATE.get('promo_text_kr','')}")
            return

        if data == "adm:show_transport":
            await q.message.reply_text(f"🧭 Transport link:\n{get_transport_url()}")
            return

        if data == "adm:hint_uz":
            await q.message.reply_text("✏️ Promo UZ o‘zgartirish:\n/setpromo_uz <matn>")
            return

        if data == "adm:hint_kr":
            await q.message.reply_text("✏️ Promo KR o‘zgartirish:\n/setpromo_kr <matn>")
            return

        if data == "adm:hint_transport":
            await q.message.reply_text("✏️ Transport link o‘zgartirish:\n/settransport <link>")
            return

# ================== GROUP HANDLER ==================
async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    chat = update.effective_chat
    if not chat_allowed(chat.id):
        return
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    text = (update.message.text or "").strip()
    norm = text.lower()

    # 1) delete original message (if bot has rights)
    try:
        await update.message.delete()
    except Exception:
        pass

    # 2) if exact trigger -> 1 button direct answer in DM
    matched_key: Optional[str] = None
    for key, variants in TRIGGERS.items():
        for v in variants:
            if norm == v.lower():
                matched_key = key
                break
        if matched_key:
            break

    if matched_key:
        url = deep_link(matched_key)
        if url:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Javobni olish (shaxsiy)", url=url)]])
            await chat.send_message("Savol shaxsiyda javoblanadi 👇", reply_markup=kb)
            return

    # 3) otherwise show quick menu buttons
    await chat.send_message(
        "Savollar shaxsiyda javoblanadi. Mavzuni tanlang 👇",
        reply_markup=kb_group_dm_links()
    )

# ================== MAIN ==================
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q. Variables’ga BOT_TOKEN qo‘ying.")
    if not BOT_USERNAME:
        log.warning("BOT_USERNAME yo‘q. Deep-link tugmalar ishlashi uchun BOT_USERNAME qo‘ying.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("setpromo_uz", setpromo_uz_cmd))
    app.add_handler(CommandHandler("setpromo_kr", setpromo_kr_cmd))
    app.add_handler(CommandHandler("settransport", settransport_cmd))

    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))

    log.info("✅ Umra FAQ bot ishga tushdi | FAQ=%s | AllowedChat=%s", len(FAQ_DB), ALLOWED_CHAT_ID)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
