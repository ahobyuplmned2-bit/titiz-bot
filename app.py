"""
بوت Titiz الذكي - نسخة موحدة
تطبيق WhatsApp Bot متقدم لمتجر Titiz
نظام ردود موحد: كل الردود (المبرمجة والمضافة من واتساب) تُعامل بنفس الطريقة
"""

from flask import Flask, request, jsonify
import requests
import json
import os
import re
import base64
from datetime import datetime
import time
import unicodedata

# استيراد الملفات المخصصة
from database import (
    init_db, add_customer, get_customer, add_product, get_all_products,
    get_product, add_to_cart, get_cart, clear_cart, remove_from_cart,
    create_order, get_order, update_order_status,
    log_action, get_statistics, load_qa, save_qa, delete_qa
)
from whatsapp_api import WhatsAppAPI, format_product_card

app = Flask(__name__)

# ===== الإعدادات العامة =====
BOT_NAME = "Titiz موظفتك الذكية نرد على جميع طلباتكم 24 ساعة"

# ===== بيانات WhatsApp =====
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAAVV1mNUcEkBRZCKz7cZAPn3Dc0NE33WUQm7kjSQ6bLJzT7iA0IswVwteUoSHInm2aW690MiEPT87UjciE9c5Bk0VQl9cMZBloQZCF3u4bZAEFrXCqrikv68EnaOPaZAZBAQXEhfCpWWNXGP68E5DPqxUa4hP5ZBeiVTqsnQZADrEHAR8zqESGtZAtn2EXWxZBI3QZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "1097018736835171")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "bot_adawat_manziliya_2026")
OWNER_NUMBER = os.environ.get("OWNER_NUMBER", "967773595571")

# ===== بيانات GitHub =====
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "ahobyuplmned2-bit/titiz-bot"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

# ===== تهيئة الخدمات =====
whatsapp = WhatsAppAPI(ACCESS_TOKEN, PHONE_NUMBER_ID)
init_db()

# ===== متغيرات الجلسات =====
user_sessions = {}
user_states = {}

# ===== منع تكرار الرسائل =====
processed_messages = {}
DEDUP_WINDOW = 30

# ===== صور المنتجات الثابتة =====
IMG_QUDOR = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/FErlTSZcVDmLLuCl.jpg"
IMG_THALAJA = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/yCftQDzESzArGegt.jpg"
IMG_FARAMA_BIG = "1722172418808924"
IMG_FARAMA_MED = "1788826688946693"
IMG_FARAMA_SML = "1340222830997132"

# ╔══════════════════════════════════════════════════════════════╗
# ║         نظام التطبيع الموحد (Unified Normalization)         ║
# ╚══════════════════════════════════════════════════════════════╝

def normalize_text(text):
    """
    تطبيع النص الموحد - يُستخدم لكل المقارنات
    يزيل: الهمزات، التشكيل، المسافات الزائدة، علامات الترقيم، ال التعريف
    يوحّد: التاء المربوطة/المفتوحة، الألف بأشكالها، الياء/ألف مقصورة
    """
    if not text:
        return ""
    text = text.strip().lower()

    # إزالة التشكيل (الفتحة، الضمة، الكسرة، السكون، الشدة، التنوين)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670]', '', text)

    # توحيد الألف بجميع أشكالها
    text = re.sub(r'[إأآٱا]', 'ا', text)

    # توحيد التاء المربوطة والهاء
    text = text.replace('ة', 'ه')

    # توحيد الياء والألف المقصورة
    text = text.replace('ى', 'ي')
    text = text.replace('ئ', 'ي')

    # توحيد الهمزات
    text = text.replace('ؤ', 'و')

    # إزالة علامات الترقيم والرموز
    text = re.sub(r'[!?.,،؟؛:»«\-_\(\)\[\]{}"\'/\\|@#\$%\^&\*\+~`\u200f\u200e\u00a0]', '', text)

    # إزالة ال التعريف من بداية الكلمات
    text = re.sub(r'\bال', '', text)

    # تقليص المسافات المتعددة
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ╔══════════════════════════════════════════════════════════════╗
# ║         نظام الردود الموحد (Unified Response System)        ║
# ╚══════════════════════════════════════════════════════════════╝
#
# كل الردود (المبرمجة في الكود + المضافة من واتساب) تُخزن في
# قاموس واحد UNIFIED_RESPONSES بنفس الشكل:
#   المفتاح = الكلمة المطبّعة (بعد normalize_text)
#   القيمة = dict مع:
#     "reply": نص الرد (أو قائمة نصوص)
#     "images": قائمة صور (اختياري) - كل عنصر {"type":"url"|"id", "src":"...", "caption":"..."}
#     "source": "builtin" أو "custom"
#
# البحث يتم بنفس الطريقة لكل الردود بدون تمييز.

UNIFIED_RESPONSES = {}

def add_response(keywords, reply, images=None, source="builtin"):
    """إضافة رد للنظام الموحد"""
    if isinstance(keywords, str):
        keywords = [keywords]
    for kw in keywords:
        normalized_kw = normalize_text(kw)
        if normalized_kw:
            UNIFIED_RESPONSES[normalized_kw] = {
                "reply": reply,
                "images": images or [],
                "source": source,
                "original_keyword": kw
            }

def remove_response(keyword):
    """حذف رد من النظام الموحد"""
    normalized_kw = normalize_text(keyword)
    if normalized_kw in UNIFIED_RESPONSES:
        del UNIFIED_RESPONSES[normalized_kw]
        return True
    return False

def find_response(msg_normalized):
    """
    البحث عن رد مطابق - نفس المنطق لكل الردود
    1. مطابقة تامة
    2. مطابقة جزئية (الكلمة المفتاحية داخل الرسالة)
    3. مطابقة عكسية (الرسالة داخل الكلمة المفتاحية)
    """
    # 1. مطابقة تامة
    if msg_normalized in UNIFIED_RESPONSES:
        return UNIFIED_RESPONSES[msg_normalized]

    # 2. مطابقة جزئية - الكلمة المفتاحية موجودة في الرسالة
    best_match = None
    best_len = 0
    for key, data in UNIFIED_RESPONSES.items():
        if len(key) > 2 and key in msg_normalized:
            # نختار أطول مطابقة (أكثر دقة)
            if len(key) > best_len:
                best_match = data
                best_len = len(key)

    if best_match:
        return best_match

    # 3. مطابقة عكسية - الرسالة موجودة في كلمة مفتاحية
    for key, data in UNIFIED_RESPONSES.items():
        if len(msg_normalized) > 2 and msg_normalized in key:
            return data

    return None

# ===== تسجيل الردود المبرمجة =====

# --- المنتجات ---
RESP_FARAMA = "🔴 *فرامة الضغطة الذكية من المائدة* 🔪\n\nالمميزات:\n✅ توفّر عليكِ 60% من وقت التقطيع\n✅ شفرات فولاذ ضد الصدأ\n✅ سهلة التنظيف والاستخدام\n✅ تقطع كمية كبيرة مرة وحدة\n\n💰 *الأسعار:*\n🔴 الكبير (MD-5266): 3,000 ريال\n🟢 الوسط (MD-5076): 2,500 ريال\n🟢 الصغير (MD-5066): 2,000 ريال\n\n🚚 التوصيل مجاني داخل المحافظة!\n⚠️ احذروا التقليد - اطلبيها باسمها من المائدة"
RESP_QUDOR = "🍲 *طقم قدور المائدة 4 قطع - هندي*\n\n✅ ستانلس ثقيل + أغطية استيل\n✅ 4 مقاسات: كبير/وسط/صغير/صغير جداً\n✅ ضمان المائدة\n\n💰 *الأسعار:*\nالكبير 3,500 | الوسط 3,000\nالصغير 2,500 | الصغير جداً 2,000\n\n🎁 *الطقم كامل:* 10,500 ريال - وفر 1,000\n🚚 توصيل مجاني لداخل المحافظة"
RESP_THALAJA = "☕ *ثلاجة شاي المائدة M213 - 0.7 لتر*\n\n✅ تحفظ الحرارة 6 ساعات\n✅ الألوان: وردي 💗 | بيج 🤎 | أزرق 💙 | كحلي\n✅ تصميم أنيق للضيافة\n\n💰 السعر: 2,500 ريال\n\n🚚 توصيل مجاني لداخل المحافظة\n⏰ الكمية محدودة"

add_response(
    ["فرامة", "فرامه", "الفرامة", "الفرامه", "فرامة الضغطة", "فرامه الضغطه",
     "فرامة الضغطه", "فرامه الضغطة", "الفرامة الذكية", "الفرامه الذكيه", "فرامة ذكية",
     "فرامه ذكيه", "عصارة", "عصاره", "العصارة", "العصاره", "فرامة المائدة", "فرامه المائده",
     "فرامة المائده", "فرامه المائدة", "فرامة خضار", "فرامه خضار", "قطاعة", "قطاعه",
     "القطاعة", "القطاعه", "مفرمة", "مفرمه", "المفرمة", "المفرمه", "خلاط", "الخلاط",
     "فرامة ضغطة", "فرامه ضغطه", "ضغطة ذكية", "ضغطه ذكيه"],
    RESP_FARAMA,
    images=[
        {"type": "id", "src": IMG_FARAMA_BIG, "caption": "🔴 الكبير MD-5266 - 3,000 ريال"},
        {"type": "id", "src": IMG_FARAMA_MED, "caption": "🟢 الوسط MD-5076 - 2,500 ريال"},
        {"type": "id", "src": IMG_FARAMA_SML, "caption": "🟢 الصغير MD-5066 - 2,000 ريال"}
    ]
)

add_response(
    ["قدور", "القدور", "قدر", "القدر", "طقم قدور", "طقم القدور",
     "قدور المائدة", "قدور المائده", "قدور هندي", "قدور ستانلس", "طقم",
     "قدور هندية", "قدور هنديه", "حلل", "الحلل", "طنجرة", "طنجره"],
    RESP_QUDOR,
    images=[{"type": "url", "src": IMG_QUDOR, "caption": RESP_QUDOR}]
)

add_response(
    ["ثلاجة", "ثلاجه", "الثلاجة", "الثلاجه", "شاي", "ثلاجة شاي",
     "ثلاجه شاي", "ثلاجة الشاي", "ثلاجه الشاي", "ترمس", "ترمز", "حافظة", "حافظه",
     "ثلاجة المائدة", "ثلاجه المائده"],
    RESP_THALAJA,
    images=[{"type": "url", "src": IMG_THALAJA, "caption": RESP_THALAJA}]
)

# --- التحيات ---
add_response(
    ["السلام عليكم", "السلام وعليكم", "السلامعليكم", "السلام عليكم ورحمة الله",
     "السلام عليكم ورحمه الله", "السلام عليكم ورحمة الله وبركاته",
     "السلام عليكم ورحمه الله وبركاته", "السلام", "سلام عليكم",
     "سلام وعليكم", "وعليكم السلام", "عليكم السلام", "السلام عليك",
     "سلام عليك", "اسلام وعليكم", "اسلام عليكم", "اسلام", "اسلام عليك"],
    "وعليكم السلام ورحمة الله 🤲✨\nنورتينا يا غالية! بايش نخدمكِ؟ 😊"
)

add_response(
    ["هلا", "هلا والله", "هلا وغلا", "هلاا", "هلااا", "يا هلا", "ياهلا"],
    "هلا وغلا فيكِ! 💛✨\nنورتي والله! بايش نخدمكِ؟ 😊"
)

add_response(
    ["مرحبا", "مرحبه", "مرحباً", "مرحبأ"],
    "مرحباً فيكِ! 🌸✨\nأهلاً وسهلاً! بايش نقدر نساعدكِ؟ 😊"
)

add_response(
    ["كيف الحال", "كيف حالك", "كيفك", "كيفكم", "شخبارك", "شخباركم",
     "شلونك", "شلونكم", "اخبارك", "أخبارك", "اشلونك", "وش اخبارك",
     "وش أخبارك", "ايش اخبارك"],
    "الحمد لله بخير! الله يسعدكِ 😊💛\nبايش نقدر نخدمكِ؟"
)

add_response(
    ["اهلا", "اهلين", "أهلا", "أهلين", "اهلاً", "أهلاً", "حياك",
     "حياك الله", "حياكم", "حياكم الله"],
    "أهلين فيكِ! 💛✨\nحياكِ الله! بايش نخدمكِ؟ 😊"
)

add_response(
    ["هاي", "هااي", "hi", "hello", "hey"],
    "هايي! 👋😊\nأهلاً فيكِ! بايش نقدر نساعدكِ؟ 💛"
)

add_response(
    ["مساء الخير", "مسا الخير", "مساءالخير", "مساء الخير عليكم",
     "مسائكم خير", "مساكم الله بالخير"],
    "مساء النور والورد! 🌙✨\nأهلاً فيكِ! بايش نخدمكِ؟ 😊"
)

add_response(
    ["صباح الخير", "صباحالخير", "صباح الخير عليكم", "صباح النور", "صباحكم خير"],
    "صباح النور والسعادة! ☀️🌺\nيسعد صباحكِ! بايش نخدمكِ؟ 😊"
)

add_response(
    ["يعطيك العافيه", "يعطيك العافية", "الله يعافيك", "الله يعافيكم",
     "يعطيكم العافيه", "يعطيكم العافية", "عافيه", "عافية"],
    "الله يعافيكِ يا قلبي! 🙏💛\nنورتينا! بايش نخدمكِ؟ 😊"
)

add_response(
    ["شكرا", "شكراً", "شكرا لك", "شكراً لك", "شكرا لكم", "مشكور",
     "مشكوره", "مشكورة", "مشكورين", "جزاك الله خير", "جزاكم الله خير",
     "تسلم", "تسلمي", "تسلمين", "يسلمو", "الله يجزاك خير"],
    "العفو يا غالية! 🙏✨\nإحنا في خدمتكِ دائماً! 😊"
)

# --- التوصيل ---
add_response(
    ["توصيل", "التوصيل", "شحن", "الشحن", "توصلون", "توصلوا", "يوصل",
     "كم التوصيل", "سعر التوصيل", "مجاني", "التوصيل مجاني"],
    "🚚 *التوصيل والشحن:*\n\n✅ داخل محافظة إب: *مجاني* تماماً!\n📦 باقي المحافظات: 2-4 أيام\n💳 الدفع عند الاستلام\n\nيعني ما فيه أي مخاطرة عليكِ 😊"
)

# --- الدفع ---
add_response(
    ["دفع", "الدفع", "كيف ادفع", "كيف الدفع", "طريقة الدفع", "طريقه الدفع",
     "حساب", "الحساب", "تحويل", "التحويل", "حسابات", "الحسابات", "نقطة جيب",
     "الكريمي", "كريمي", "جيب"],
    "💳 *طرق الدفع:*\n\n✅ *الدفع عند الاستلام:*\nنحط المنتج لأقرب نقطة منكِ وتدفعي وقت الاستلام 👌\n\n✅ *التحويل المسبق:*\nتدفعي وإحنا نوصل لكِ الطلب لباب بيتكِ 🚚\n\n💰 *حسابات التحويل:*\n\n🟢 *نقطة جيب:* 906072\n🟡 *الكريمي نقطة حاسب:* 1202686\n🏦 *إيداع عبر الكريمي:* 3122678098\n\nاختاري الطريقة اللي تناسبكِ 😊"
)

# --- الضمان ---
add_response(
    ["ضمان", "الضمان", "استبدال", "الاستبدال", "استرجاع", "الاسترجاع",
     "ارجاع", "الارجاع", "ترجيع", "لو ما عجبني", "اذا ما عجبني"],
    "🔄 *الضمان والاستبدال:*\n\n✅ استبدال خلال 7 أيام من الاستلام\n✅ استرجاع خلال 3 أيام (بحالته الأصلية)\n✅ ضمان المائدة على المنتجات\n\nإحنا واثقين من جودة منتجاتنا 👌"
)

# --- الثقة ---
add_response(
    ["ثقة", "الثقة", "مصداقية", "كيف نثق", "كيف اثق", "نثق فيكم",
     "اثق فيكم", "صادقين", "تكذبون", "نصب", "احتيال"],
    "🤝 *ليش تثقين فينا:*\n\n✅ عندنا محلين في إب تقدري تزورينا 🏪\n✅ الدفع عند الاستلام - ما نطلب فلوس مقدماً\n✅ استبدال خلال 7 أيام لو ما عجبكِ\n✅ زبائننا كثير والحمد لله راضين\n✅ نشتغل بسمعتنا وما نغش أي زبون\n\n📍 *عناويننا:*\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم\n\nجربي واحكمي بنفسكِ 😊👌"
)

# --- الموقع ---
add_response(
    ["الموقع", "موقع", "العنوان", "عنوان", "وينكم", "وين المحل",
     "وين موقعكم", "فين المحل", "فين موقعكم", "المحل", "محلكم",
     "مكانكم", "فينكم", "الفرع", "الفروع", "فروعكم"],
    "📍 *مواقع محلات Titiz:*\n\n🏪 *الفرع الأول:*\nإب - بوابة ملعب الكبسي الخلفية\nنهاية طلعة صرافة الكريمي\n\n🏪 *الفرع الثاني:*\nالسوق المركزي القديم\nأمام صرافة فيصل الخطيب\n\n✅ نستقبلكِ بأي وقت!"
)

# --- الطلب ---
add_response(
    ["اطلب", "أطلب", "ابي اطلب", "أبي أطلب", "ابغى", "أبغى",
     "اشتي اطلب", "بدي اطلب", "طلبيه", "طلبية"],
    "🛒 *لإتمام الطلب:*\n\nاكتبي *اكمل الطلب* وبنكمل معكِ الخطوات 😊\n\nأو أضيفي منتجات للسلة أولاً:\nاكتبي اسم المنتج وبنضيفه لكِ ✅\n\n💳 الدفع عند الاستلام أو تحويل\n📦 التوصيل مجاني داخل المحافظة!"
)

# --- ايش عندكم ---
RESP_PRODUCTS_ASK = "🏠 أهلاً فيكِ يا غالية! ✨\n\nلدينا جميع الأدوات المنزلية ومستلزمات المطابخ 🍳\n\nايش بدكِ أنتِ من منتج؟ 😊\n\nمثلاً:\n🍲 اكتبي *قدور* - طقم قدور ستانلس\n☕ اكتبي *ثلاجة* - ثلاجة شاي أنيقة\n🔪 اكتبي *فرامة* - فرامة الضغطة الذكية\n\nأو اكتبي *القائمة* لعرض كل الخيارات 📋"
add_response(
    ["ايش عندكم", "ايش معاكم", "وش عندكم", "ايش تبيعون", "ايش تبيعو",
     "ايش منتجاتكم", "وش منتجاتكم", "ايش البضاعة", "ايش البضاعه",
     "منتجات", "المنتجات", "بضاعة", "البضاعة", "البضاعه",
     "ايش في", "وش في", "عندكم ايش", "معاكم ايش"],
    RESP_PRODUCTS_ASK
)

# --- مكان الاستلام ---
add_response(
    ["وين تحطوا", "وين تحطون", "فين تحطوا", "وين توصلوا",
     "فين توصلوا", "وين اخذه", "وين اخذ الطلب", "فين اخذه",
     "وين الاستلام", "فين الاستلام", "من وين استلم",
     "الاستلام", "طريقة الاستلام", "طريقه الاستلام"],
    "📦 وين تحبين نحط لكِ المنتج؟ 🤔\n\nنقدر نحطه في أي مكان قريب منكِ:\n\n🏪 محل قريب من بيتكِ\n🛍️ بقالة في حارتكِ\n📍 أي نقطة تحدديها\n\nأرسلي لنا اسم المكان أو المنطقة وإحنا نوصله لأقرب نقطة منكِ 😊👌"
)

# --- الوداع ---
add_response(
    ["مع السلامة", "مع السلامه", "باي", "الله يحفظك", "في أمان الله",
     "في امان الله", "يلا باي", "خلاص شكرا", "تمام شكرا"],
    "مع السلامة يا غالية! 💛👋\nنورتينا والله!\nإحنا هنا بأي وقت تحتاجينا 😊\nلا تنسينا! ❤️"
)

WELCOME_MESSAGE = "يا غالية خلينا بموضوعنا 😊✨\nإحنا محل *Titiz* للأدوات المنزلية 🏠\n\nعندنا منتجات حلوة وأسعار تناسب الجميع 👌\nوالتوصيل مجاني لباب بيتكِ! 🚚\n\nاكتبي اسم المنتج اللي تبينه 😍\nأو اكتبي *القائمة* لعرض الخيارات 📋"

# ===== تحميل الردود المخصصة من قاعدة البيانات =====
def load_custom_responses():
    """تحميل الردود المضافة من واتساب إلى النظام الموحد"""
    try:
        qas = load_qa()
        for keyword, answer in qas.items():
            add_response(keyword, answer, source="custom")
    except:
        pass

# تحميل عند بدء التشغيل
load_custom_responses()


# ╔══════════════════════════════════════════════════════════════╗
# ║                    دوال مساعدة                              ║
# ╚══════════════════════════════════════════════════════════════╝

def github_load(filename):
    """تحميل ملف من GitHub"""
    try:
        url = f"{GITHUB_API}/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content = resp.json().get("content", "")
            decoded = base64.b64decode(content).decode("utf-8")
            return json.loads(decoded), resp.json().get("sha", "")
        return {}, ""
    except:
        return {}, ""

def github_save(filename, data, sha=""):
    """حفظ ملف على GitHub"""
    if not GITHUB_TOKEN:
        return False
    try:
        url = f"{GITHUB_API}/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        content = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")
        payload = {"message": f"Update {filename}", "content": content}
        if sha:
            payload["sha"] = sha
        else:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload["sha"] = resp.json().get("sha", "")
        requests.put(url, headers=headers, json=payload, timeout=10)
        return True
    except:
        return False

def send_message(to, text):
    return whatsapp.send_message(to, text)

def send_image(to, image_url, caption=""):
    return whatsapp.send_image(to, image_url, caption)

def send_image_by_id(to, media_id, caption=""):
    return whatsapp.send_image_by_id(to, media_id, caption)

def send_buttons(to, text, buttons):
    return whatsapp.send_buttons(to, text, buttons)

def send_list(to, text, button_text, sections):
    return whatsapp.send_list(to, text, button_text, sections)

def notify_owner(sender, msg_body):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    notification = f"📩 *رسالة جديدة*\n\n👤 الرقم: {sender}\n💬 الرسالة: {msg_body}\n🕐 الوقت: {now}"
    send_message(OWNER_NUMBER, notification)

def notify_owner_new_order(order_number, phone, name, address, items, total, payment_method):
    items_text = ""
    for item in items:
        items_text += f"  • {item['name']} × {item.get('qty',1)} = {item.get('total',0)} ريال\n"
    msg = f"🔔 *طلب جديد!*\n\n📋 رقم الطلب: *{order_number}*\n👤 الاسم: {name}\n📱 الرقم: {phone}\n📍 العنوان: {address}\n\n🛒 *المنتجات:*\n{items_text}\n💰 *الإجمالي: {int(total)} ريال*\n💳 الدفع: {payment_method}"
    send_message(OWNER_NUMBER, msg)

def send_response(to, response_data):
    """إرسال رد موحد (نص + صور)"""
    reply = response_data["reply"]
    images = response_data.get("images", [])

    # إرسال النص
    if isinstance(reply, list):
        for r in reply:
            send_message(to, r)
    elif images and len(images) == 1 and images[0].get("caption") == reply:
        # صورة واحدة مع نفس النص = نرسل صورة بكابشن فقط
        img = images[0]
        if img["type"] == "url":
            send_image(to, img["src"], reply)
        else:
            send_image_by_id(to, img["src"], reply)
        return
    else:
        send_message(to, reply)

    # إرسال الصور
    for img in images:
        if img["type"] == "url":
            send_image(to, img["src"], img.get("caption", ""))
        else:
            send_image_by_id(to, img["src"], img.get("caption", ""))

# ===== القائمة التفاعلية =====
def send_main_menu(to):
    sections = [{
        "title": "الخدمات",
        "rows": [
            {"id": "menu_products", "title": "🛍️ تصفح المنتجات", "description": "عرض جميع المنتجات"},
            {"id": "menu_cart", "title": "🛒 السلة", "description": "عرض سلة المشتريات"},
            {"id": "menu_orders", "title": "📦 طلباتي", "description": "متابعة طلباتك"},
            {"id": "menu_payment", "title": "💳 طرق الدفع", "description": "حسابات التحويل"},
            {"id": "menu_location", "title": "📍 مواقعنا", "description": "عناوين الفروع"},
            {"id": "menu_contact", "title": "📞 التواصل معنا", "description": "للاستفسارات"}
        ]
    }]
    send_list(to, "🏠 *أهلاً بكِ في Titiz!*\n\nاختاري من القائمة:", "📋 القائمة", sections)


# ╔══════════════════════════════════════════════════════════════╗
# ║                 معالجة أوامر المالك                          ║
# ╚══════════════════════════════════════════════════════════════╝

def handle_owner_command(sender, msg_body, msg_normalized, message):
    """معالجة أوامر المالك - ترجع True إذا تم التعامل مع الأمر"""

    # === رد على زبون ===
    if msg_normalized.startswith("رد "):
        parts = msg_body.split(" ", 2)
        if len(parts) == 3:
            send_message(parts[1], parts[2])
            send_message(OWNER_NUMBER, f"✅ تم إرسال ردك للزبون {parts[1]}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: رد [رقم] [الرسالة]")
        return True

    # === إضافة رد (يدخل نفس النظام الموحد) ===
    if msg_normalized.startswith("اضف رد "):
        # الصيغة: اضف رد [الكلمة المفتاحية] | [الرد]
        add_text = msg_body[8:].strip()
        if "|" in add_text:
            parts = [p.strip() for p in add_text.split("|", 1)]
            keyword = parts[0]
            answer = parts[1] if len(parts) > 1 else ""
            if keyword and answer:
                # حفظ في قاعدة البيانات
                save_qa(keyword, answer)
                # إضافة للنظام الموحد فوراً
                add_response(keyword, answer, source="custom")
                send_message(OWNER_NUMBER, f"✅ تم إضافة الرد:\n🔑 الكلمة: {keyword}\n💬 الرد: {answer}\n\nالآن لو أي زبون كتب '{keyword}' بيرد عليه تلقائي ✅")
            else:
                send_message(OWNER_NUMBER, "❌ الصيغة: اضف رد [الكلمة] | [الرد]")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: اضف رد [الكلمة] | [الرد]\n\nمثال: اضف رد متى يوصل | يوصل خلال 24 ساعة")
        return True

    # === حذف رد ===
    if msg_normalized.startswith("حذف رد "):
        keyword = msg_body[7:].strip()
        # حذف من قاعدة البيانات
        delete_qa(keyword)
        # حذف من النظام الموحد
        removed = remove_response(keyword)
        if removed:
            send_message(OWNER_NUMBER, f"✅ تم حذف الرد: {keyword}")
        else:
            send_message(OWNER_NUMBER, f"⚠️ تم حذفه من القاعدة (قد يكون غير موجود في الذاكرة)")
        return True

    # === عرض الردود المخصصة ===
    if msg_normalized in ["ردودي", "الردود", "ردود"]:
        qas = load_qa()
        if qas:
            qa_list = "📋 *الردود المخصصة:*\n\n"
            for i, (k, v) in enumerate(qas.items(), 1):
                short_v = v[:50] + "..." if len(v) > 50 else v
                qa_list += f"{i}. 🔑 *{k}*\n   💬 {short_v}\n\n"
            qa_list += "لحذف رد: حذف رد [الكلمة]"
            send_message(OWNER_NUMBER, qa_list)
        else:
            send_message(OWNER_NUMBER, "📋 لا توجد ردود مخصصة\n\nلإضافة رد: اضف رد [الكلمة] | [الرد]")
        return True

    # === إضافة منتج ===
    if msg_normalized.startswith("اضف ") and not msg_normalized.startswith("اضف رد"):
        add_text = msg_body[4:].strip()
        if "|" in add_text:
            parts = [p.strip() for p in add_text.split("|")]
            product_name = parts[0] if len(parts) > 0 else ""
            price_value = parts[1] if len(parts) > 1 else "0"
            product_desc = parts[2] if len(parts) > 2 else ""
            keywords_str = parts[3] if len(parts) > 3 else ""
            price_num = re.search(r'\d+', price_value)
            price_val = float(price_num.group()) if price_num else 0
            if product_name:
                add_product(product_name, price_val, product_desc, "", 100, keywords_str)
                send_message(OWNER_NUMBER, f"✅ تم إضافة المنتج:\n📦 {product_name}\n💰 {int(price_val)} ريال\n📝 {product_desc}\n🔑 كلمات: {keywords_str or 'لا يوجد'}\n\nلإضافة صورة: أرسل صورة مع كابشن فيه اسم المنتج")
            else:
                send_message(OWNER_NUMBER, "❌ الصيغة: اضف [اسم] | [سعر] | [وصف] | [كلمات مفتاحية]")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: اضف [اسم] | [سعر] | [وصف] | [كلمات مفتاحية]")
        return True

    # === تعديل سعر ===
    if msg_normalized.startswith("عدل سعر "):
        text = msg_body[9:].strip()
        price_match = re.search(r'\b(\d+)\b', text)
        if price_match:
            product_name = text[:price_match.start()].strip()
            new_price = float(price_match.group(1))
            from database import db_lock, DB_PATH
            import sqlite3 as _sqlite3
            with db_lock:
                conn = _sqlite3.connect(DB_PATH)
                conn.execute("UPDATE products SET price=? WHERE name LIKE ?", (new_price, f"%{product_name}%"))
                conn.commit()
                conn.close()
            send_message(OWNER_NUMBER, f"✅ تم تعديل سعر {product_name} إلى {int(new_price)} ريال")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: عدل سعر [اسم المنتج] [السعر الجديد]")
        return True

    # === حذف منتج ===
    if msg_normalized.startswith("حذف ") and not msg_normalized.startswith("حذف رد"):
        product_name = msg_body[4:].strip()
        from database import db_lock, DB_PATH
        import sqlite3 as _sqlite3
        with db_lock:
            conn = _sqlite3.connect(DB_PATH)
            cursor = conn.execute("DELETE FROM products WHERE name LIKE ?", (f"%{product_name}%",))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        if deleted:
            send_message(OWNER_NUMBER, f"✅ تم حذف المنتج: {product_name}")
        else:
            send_message(OWNER_NUMBER, f"❌ المنتج '{product_name}' غير موجود")
        return True

    # === المخزن ===
    if msg_normalized in ["مخزن", "منتجاتي"]:
        products = get_all_products()
        if products:
            product_list = "📦 *المنتجات المحفوظة:*\n\n"
            for i, p in enumerate(products, 1):
                has_img = "🖼️" if p.get("image_id") else "❌"
                product_list += f"{i}. *{p['name']}* - {int(p['price'])} ريال {has_img}\n"
            product_list += f"\n📊 إجمالي: {len(products)} منتج"
            send_message(OWNER_NUMBER, product_list)
        else:
            send_message(OWNER_NUMBER, "📦 المخزن فارغ")
        return True

    # === الزبائن ===
    if msg_normalized in ["زبائن", "عملاء"]:
        from database import db_lock, DB_PATH
        import sqlite3 as _sqlite3
        with db_lock:
            conn = _sqlite3.connect(DB_PATH)
            conn.row_factory = _sqlite3.Row
            customers = conn.execute("SELECT * FROM customers ORDER BY updated_at DESC LIMIT 20").fetchall()
            conn.close()
        if customers:
            cust_list = "📋 *قائمة العملاء:*\n\n"
            for i, c in enumerate(customers, 1):
                name = c["name"] or "بدون اسم"
                cust_list += f"{i}. 👤 {name}\n   📱 {c['phone_number']}\n   📊 {c['order_count']} طلب\n\n"
            send_message(OWNER_NUMBER, cust_list)
        else:
            send_message(OWNER_NUMBER, "📋 لا يوجد عملاء")
        return True

    # === الطلبات ===
    if msg_normalized in ["طلبات"]:
        from database import db_lock, DB_PATH
        import sqlite3 as _sqlite3
        with db_lock:
            conn = _sqlite3.connect(DB_PATH)
            conn.row_factory = _sqlite3.Row
            orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10").fetchall()
            conn.close()
        if orders:
            orders_list = "📋 *آخر الطلبات:*\n\n"
            for o in orders:
                orders_list += f"📦 *{o['order_number']}* | {o['order_status']} | {int(o['total_price'])} ريال\n"
            send_message(OWNER_NUMBER, orders_list)
        else:
            send_message(OWNER_NUMBER, "📋 لا توجد طلبات")
        return True

    # === تغيير حالة طلب ===
    if msg_normalized.startswith("حاله ") or msg_normalized.startswith("حالة "):
        parts = msg_body.split(" ", 2)
        if len(parts) >= 3:
            order_num = parts[1].strip().upper()
            if not order_num.startswith("ORD-"):
                order_num = f"ORD-{order_num.zfill(6)}"
            new_status = parts[2].strip()
            update_order_status(order_num, new_status)
            send_message(OWNER_NUMBER, f"✅ تم تحديث حالة {order_num} إلى: {new_status}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: حالة [رقم الطلب] [الحالة الجديدة]")
        return True

    # === الإحصائيات ===
    if msg_normalized in ["احصائيات", "احصاءات", "stats"]:
        stats = get_statistics()
        msg = f"📊 *إحصائيات المتجر:*\n\n📦 إجمالي الطلبات: {stats['total_orders']}\n💰 إجمالي المبيعات: {int(stats['total_sales'])} ريال\n👥 عدد العملاء: {stats['total_customers']}"
        send_message(OWNER_NUMBER, msg)
        return True

    # === نسخ احتياطي ===
    if msg_normalized in ["نسخ احتياطي", "نسخه احتياطيه", "backup"]:
        try:
            products = get_all_products()
            products_dict = {}
            for p in products:
                products_dict[p["name"]] = {
                    "name": p["name"], "price": str(int(p["price"])),
                    "description": p.get("description", ""),
                    "keywords": p.get("keywords", "").split(",") if p.get("keywords") else [],
                    "image_id": p.get("image_id", "")
                }
            github_save("products.json", products_dict)
            qas = load_qa()
            github_save("qa.json", qas)
            send_message(OWNER_NUMBER, "✅ تم حفظ نسخة احتياطية على GitHub")
        except Exception as e:
            send_message(OWNER_NUMBER, f"❌ خطأ: {str(e)}")
        return True

    # === أوامر المساعدة ===
    if msg_normalized in ["اوامر", "مساعده", "مساعدة", "help"]:
        help_text = "📋 *أوامر الإدارة:*\n\n"
        help_text += "📦 *المنتجات:*\n"
        help_text += "• اضف [اسم] | [سعر] | [وصف] | [كلمات]\n"
        help_text += "• حذف [اسم المنتج]\n"
        help_text += "• عدل سعر [اسم] [السعر]\n"
        help_text += "• مخزن\n\n"
        help_text += "💬 *الردود:*\n"
        help_text += "• اضف رد [الكلمة] | [الرد]\n"
        help_text += "• حذف رد [الكلمة]\n"
        help_text += "• ردودي\n\n"
        help_text += "📊 *أخرى:*\n"
        help_text += "• رد [رقم] [الرسالة]\n"
        help_text += "• زبائن\n"
        help_text += "• طلبات\n"
        help_text += "• حالة [رقم] [الحالة]\n"
        help_text += "• احصائيات\n"
        help_text += "• نسخ احتياطي"
        send_message(OWNER_NUMBER, help_text)
        return True

    # === رفع صورة لمنتج ===
    if message.get("type") == "image":
        image_info = message.get("image", {})
        media_id = image_info.get("id", "")
        caption = image_info.get("caption", "").strip()
        if caption and media_id:
            from database import db_lock, DB_PATH
            import sqlite3 as _sqlite3
            with db_lock:
                conn = _sqlite3.connect(DB_PATH)
                cursor = conn.execute("UPDATE products SET image_id=? WHERE name LIKE ?", (media_id, f"%{caption}%"))
                if cursor.rowcount == 0:
                    add_product(caption, 0, "", media_id, 100, "")
                    send_message(OWNER_NUMBER, f"✅ تم حفظ الصورة كمنتج جديد: {caption}\nعدل السعر: عدل سعر {caption} [السعر]")
                else:
                    send_message(OWNER_NUMBER, f"✅ تم إضافة صورة للمنتج: {caption}")
                conn.commit()
                conn.close()
        elif media_id and not caption:
            send_message(OWNER_NUMBER, "❌ أرسل الصورة مع كابشن فيه اسم المنتج")
        return True

    return False


# ╔══════════════════════════════════════════════════════════════╗
# ║                 معالجة رسائل العملاء                         ║
# ╚══════════════════════════════════════════════════════════════╝

def handle_customer_message(sender, msg_body, msg_normalized, message):
    """معالجة رسائل العملاء"""
    state = user_states.get(sender, "")

    # === حالات الجلسة ===

    if state == "awaiting_name":
        user_states[sender] = "awaiting_address"
        user_sessions[sender] = {"name": msg_body.strip()}
        send_message(sender, "📍 تمام! الحين أرسلي لنا عنوان التوصيل (المنطقة أو أقرب نقطة) 😊")
        return

    if state == "awaiting_address":
        session_data = user_sessions.get(sender, {})
        session_data["address"] = msg_body.strip()
        user_sessions[sender] = session_data
        user_states[sender] = "awaiting_payment"
        send_buttons(sender,
            "💳 *اختاري طريقة الدفع:*\n\n✅ الدفع عند الاستلام\n✅ التحويل المسبق",
            [{"id": "pay_cod", "title": "💵 عند الاستلام"},
             {"id": "pay_transfer", "title": "💳 تحويل مسبق"}])
        return

    if state == "awaiting_payment":
        session_data = user_sessions.get(sender, {})
        if "استلام" in msg_normalized or msg_normalized == "pay_cod" or msg_normalized == "1":
            cart_items = get_cart(sender)
            if cart_items:
                items = [{"name": item["name"], "qty": item["quantity"],
                          "price": item["price"], "total": item["price"] * item["quantity"]}
                         for item in cart_items]
                total = sum(i["total"] for i in items)
                name = session_data.get("name", "")
                address = session_data.get("address", "")
                add_customer(sender, name, address)
                customer = get_customer(sender)
                order_number, _ = create_order(customer["id"], items, total, "الدفع عند الاستلام")
                clear_cart(sender)
                user_states.pop(sender, None)
                user_sessions.pop(sender, None)
                send_message(sender, f"✅ *تم تأكيد طلبك بنجاح!*\n\n📋 رقم الطلب: *{order_number}*\n💰 الإجمالي: {int(total)} ريال\n💵 الدفع: عند الاستلام\n📍 العنوان: {address}\n\n🚚 سيتم توصيل طلبك قريباً!\nشكراً لثقتكِ بنا يا غالية 💛😊")
                notify_owner_new_order(order_number, sender, name, address, items, total, "الدفع عند الاستلام")
            else:
                user_states.pop(sender, None)
                send_message(sender, "❌ السلة فارغة! أضيفي منتجات أولاً 😊")
            return
        elif "تحويل" in msg_normalized or "مسبق" in msg_normalized or msg_normalized == "pay_transfer" or msg_normalized == "2":
            user_states[sender] = "awaiting_transfer_proof"
            send_message(sender, "💰 *حسابات التحويل:*\n\n🟢 *نقطة جيب:* 906072\n🟡 *الكريمي نقطة حاسب:* 1202686\n🏦 *إيداع عبر الكريمي:* 3122678098\n\n📸 بعد التحويل أرسلي لنا صورة إشعار التحويل ✅")
            return
        else:
            send_buttons(sender, "اختاري طريقة الدفع:",
                [{"id": "pay_cod", "title": "💵 عند الاستلام"},
                 {"id": "pay_transfer", "title": "💳 تحويل مسبق"}])
            return

    if state == "awaiting_transfer_proof":
        if message.get("type") == "image":
            session_data = user_sessions.get(sender, {})
            cart_items = get_cart(sender)
            if cart_items:
                items = [{"name": item["name"], "qty": item["quantity"],
                          "price": item["price"], "total": item["price"] * item["quantity"]}
                         for item in cart_items]
                total = sum(i["total"] for i in items)
                name = session_data.get("name", "")
                address = session_data.get("address", "")
                add_customer(sender, name, address)
                customer = get_customer(sender)
                order_number, _ = create_order(customer["id"], items, total, "تحويل مسبق")
                clear_cart(sender)
                user_states.pop(sender, None)
                user_sessions.pop(sender, None)
                send_message(sender, f"✅ *تم استلام طلبك!*\n\n📋 رقم الطلب: *{order_number}*\n💰 الإجمالي: {int(total)} ريال\n💳 الدفع: تحويل مسبق\n\n⏳ جاري مراجعة الدفع...\nسنؤكد لكِ خلال دقائق 😊")
                notify_owner_new_order(order_number, sender, name, address, items, total, "تحويل مسبق")
                send_message(OWNER_NUMBER, f"📸 صورة إشعار التحويل للطلب {order_number}")
            else:
                user_states.pop(sender, None)
                send_message(sender, "❌ السلة فارغة!")
            return
        else:
            send_message(sender, "📸 أرسلي صورة إشعار التحويل من فضلكِ 😊")
            return

    # اختيار من قائمة منتجات
    if state == "product_list" and msg_normalized.isdigit():
        choice = int(msg_normalized)
        products_list = user_sessions.get(sender, [])
        if isinstance(products_list, list) and 1 <= choice <= len(products_list):
            found = products_list[choice - 1]
            user_states.pop(sender, None)
            user_sessions.pop(sender, None)
            product_reply = format_product_card(found)
            if found.get('image_id'):
                send_image_by_id(sender, found['image_id'], product_reply)
            else:
                send_message(sender, product_reply)
            return
        else:
            send_message(sender, f"❌ اختاري رقم من 1 إلى {len(products_list) if isinstance(products_list, list) else 0}")
            return

    # مسح الجلسة
    if state == "product_list" and not msg_normalized.isdigit():
        user_states.pop(sender, None)
        user_sessions.pop(sender, None)

    # === القائمة التفاعلية ===
    if msg_normalized in [normalize_text(x) for x in ["القائمة", "القائمه", "قائمة", "قائمه", "menu", "ابدا", "ابدأ", "start"]]:
        send_main_menu(sender)
        return

    # === أوامر السلة ===
    if msg_normalized in [normalize_text(x) for x in ["السلة", "السله", "سلة", "سله", "عربتي", "cart", "menu_cart"]]:
        cart_items = get_cart(sender)
        if cart_items:
            cart_text = "🛒 *سلة المشتريات:*\n\n"
            total = 0
            for item in cart_items:
                item_total = item["price"] * item["quantity"]
                total += item_total
                cart_text += f"  • {item['name']} × {item['quantity']} = {int(item_total)} ريال\n"
            cart_text += f"\n💰 *الإجمالي: {int(total)} ريال*\n🚚 التوصيل: مجاني\n\nاكتبي *اكمل الطلب* لإتمام الشراء ✅\nأو *افرغ السلة* لتفريغها 🗑️"
            send_message(sender, cart_text)
        else:
            send_message(sender, "🛒 السلة فارغة!\n\nاكتبي اسم المنتج اللي تبينه 😊")
        return

    if msg_normalized in [normalize_text(x) for x in ["افرغ السلة", "افرغ السله", "تفريغ السلة", "مسح السلة"]]:
        clear_cart(sender)
        send_message(sender, "🗑️ تم تفريغ السلة ✅")
        return

    # إضافة للسلة
    add_cart_prefixes = [normalize_text("اضف للسلة"), normalize_text("اضيف")]
    for prefix in add_cart_prefixes:
        if msg_normalized.startswith(prefix + " "):
            product_name = msg_normalized[len(prefix):].strip()
            products = get_all_products()
            for p in products:
                p_norm = normalize_text(p['name'])
                if product_name in p_norm or p_norm in product_name:
                    add_to_cart(sender, p['id'], 1)
                    send_message(sender, f"✅ تم إضافة *{p['name']}* للسلة!\n💰 السعر: {int(p['price'])} ريال\n\nاكتبي *السلة* لعرض المشتريات\nأو *اكمل الطلب* لإتمام الشراء 😊")
                    return
            send_message(sender, f"❌ ما لقينا المنتج\nجربي اسم ثاني 😊")
            return

    # إكمال الطلب
    if msg_normalized in [normalize_text(x) for x in ["اكمل الطلب", "اكمل", "تأكيد", "تاكيد", "اكمال الطلب", "checkout"]]:
        cart_items = get_cart(sender)
        if not cart_items:
            send_message(sender, "❌ السلة فارغة! أضيفي منتجات أولاً 😊")
            return
        total = sum(item["price"] * item["quantity"] for item in cart_items)
        summary = "🛒 *ملخص طلبك:*\n\n"
        for item in cart_items:
            summary += f"  • {item['name']} × {item['quantity']} = {int(item['price'] * item['quantity'])} ريال\n"
        summary += f"\n💰 *الإجمالي: {int(total)} ريال*\n🚚 التوصيل: مجاني"
        send_message(sender, summary)
        customer = get_customer(sender)
        if customer and customer.get("name"):
            user_sessions[sender] = {"name": customer["name"], "address": customer.get("address", "")}
            user_states[sender] = "awaiting_payment"
            send_buttons(sender, f"👤 الاسم: {customer['name']}\n📍 العنوان: {customer.get('address','غير محدد')}\n\nبيانات صحيحة؟",
                [{"id": "pay_cod", "title": "✅ صحيحة، أكملي"},
                 {"id": "change_info", "title": "✏️ تعديل البيانات"}])
        else:
            user_states[sender] = "awaiting_name"
            send_message(sender, "👤 ايش اسمكِ الكريم؟ 😊")
        return

    if msg_normalized == "change_info":
        user_states[sender] = "awaiting_name"
        send_message(sender, "👤 ايش اسمكِ الكريم؟ 😊")
        return

    # طلباتي
    if msg_normalized in [normalize_text(x) for x in ["طلباتي", "menu_orders"]]:
        from database import db_lock, DB_PATH
        import sqlite3 as _sqlite3
        customer = get_customer(sender)
        if customer:
            with db_lock:
                conn = _sqlite3.connect(DB_PATH)
                conn.row_factory = _sqlite3.Row
                orders = conn.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC LIMIT 5", (customer["id"],)).fetchall()
                conn.close()
            if orders:
                orders_text = "📦 *طلباتك:*\n\n"
                for o in orders:
                    orders_text += f"📋 *{o['order_number']}* | {o['order_status']} | {int(o['total_price'])} ريال\n"
                send_message(sender, orders_text)
            else:
                send_message(sender, "📦 ما عندكِ طلبات سابقة")
        else:
            send_message(sender, "📦 ما عندكِ طلبات سابقة")
        return

    # أزرار القائمة التفاعلية
    if msg_normalized == "menu_products":
        send_message(sender, RESP_PRODUCTS_ASK)
        return
    if msg_normalized == "menu_payment":
        resp = find_response(normalize_text("الدفع"))
        if resp:
            send_response(sender, resp)
        return
    if msg_normalized == "menu_location":
        resp = find_response(normalize_text("الموقع"))
        if resp:
            send_response(sender, resp)
        return
    if msg_normalized == "menu_contact":
        send_message(sender, "📞 *التواصل معنا:*\n\nراسلينا هنا وبنرد عليكِ بأسرع وقت 😊\n\n📍 أو زورينا في أحد فروعنا:\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم")
        return

    # ╔══════════════════════════════════════════════════════════╗
    # ║     البحث الموحد في كل الردود (مبرمجة + مخصصة)         ║
    # ╚══════════════════════════════════════════════════════════╝

    response_data = find_response(msg_normalized)
    if response_data:
        send_response(sender, response_data)
        return

    # === البحث في المنتجات (قاعدة البيانات) ===
    products = get_all_products()
    matching = []
    for p in products:
        p_name = normalize_text(p['name'])
        p_keywords = normalize_text(p.get('keywords', '') or '')
        if msg_normalized in p_name or p_name in msg_normalized:
            matching.append(p)
        elif p_keywords:
            kw_list = [normalize_text(k.strip()) for k in p_keywords.split(",")]
            for kw in kw_list:
                if kw and (msg_normalized in kw or kw in msg_normalized):
                    matching.append(p)
                    break

    if len(matching) == 1:
        found = matching[0]
        product_reply = format_product_card(found)
        if found.get('image_id'):
            send_image_by_id(sender, found['image_id'], product_reply)
        else:
            send_message(sender, product_reply)
        return
    elif len(matching) > 1:
        user_sessions[sender] = matching
        user_states[sender] = "product_list"
        list_reply = "🔍 وجدنا المنتجات التالية:\n\n"
        for i, p in enumerate(matching[:10], 1):
            list_reply += f"{i}- {p['name']} ({int(p['price'])} ريال)\n"
        list_reply += "\n✍️ أرسلي رقم المنتج اللي تبينه 😊"
        send_message(sender, list_reply)
        return

    # === رد افتراضي (آخر شي بعد كل البحث) ===
    send_message(sender, WELCOME_MESSAGE)


# ╔══════════════════════════════════════════════════════════════╗
# ║                    Webhook Routes                           ║
# ╚══════════════════════════════════════════════════════════════╝

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        message = value["messages"][0]
        message_id = message.get("id", "")
        sender = message["from"]

        # منع التكرار
        now_ts = time.time()
        if message_id in processed_messages:
            return jsonify({"status": "ok"}), 200
        processed_messages[message_id] = now_ts
        old_keys = [k for k, v in processed_messages.items() if now_ts - v > DEDUP_WINDOW]
        for k in old_keys:
            del processed_messages[k]

        # Mark as Read
        whatsapp.mark_as_read(message_id)

        # استخراج النص
        msg_body = ""
        if message.get("type") == "text":
            msg_body = message.get("text", {}).get("body", "").strip()
        elif message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                msg_body = interactive.get("button_reply", {}).get("id", "")
            elif interactive.get("type") == "list_reply":
                msg_body = interactive.get("list_reply", {}).get("id", "")
        elif message.get("type") == "image":
            msg_body = message.get("image", {}).get("caption", "").strip()

        msg_normalized = normalize_text(msg_body)

        # تأخير بسيط
        time.sleep(1)

        # تحديث بيانات العميل
        if sender != OWNER_NUMBER:
            add_customer(sender)

        # إشعار المالك
        if sender != OWNER_NUMBER and msg_body:
            notify_owner(sender, msg_body)

        # معالجة أوامر المالك
        if sender == OWNER_NUMBER:
            if handle_owner_command(sender, msg_body, msg_normalized, message):
                return jsonify({"status": "ok"}), 200

        # معالجة رسائل العملاء (والمالك للاختبار)
        handle_customer_message(sender, msg_body, msg_normalized, message)

    except (KeyError, IndexError):
        pass
    except Exception as e:
        print(f"خطأ: {e}")

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def home():
    return f"✅ {BOT_NAME} يعمل بنجاح!", 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
