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
from threading import Lock, Thread

# استيراد الملفات المخصصة
from database import (
    init_db, add_customer, get_customer, add_product, get_all_products,
    get_product, add_to_cart, get_cart, clear_cart, remove_from_cart,
    create_order, get_order, update_order_status, update_cart_quantity,
    log_action, get_statistics, load_qa, save_qa, delete_qa,
    get_orders, get_customer_orders, get_customers, search_customers,
    update_order_payment_proof, save_user_session, load_user_session,
    delete_user_session, schedule_customer_followup,
    cancel_customer_followup, get_due_customer_followups,
    mark_customer_followup_sent, get_customer_followup,
    record_contact, has_contact, queue_pending_reply,
    get_pending_replies, mark_pending_reply_sent
)
from whatsapp_api import WhatsAppAPI, format_product_card

app = Flask(__name__)

# ===== الإعدادات العامة =====
BOT_NAME = "Titiz موظفتك الذكية، نرد على جميع طلباتكم 24 ساعة"

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

# ===== تذكير استفسار المنتج وتقييم الرضا =====
PRODUCT_FOLLOWUP_DELAY_SECONDS = max(
    int(os.environ.get("PRODUCT_FOLLOWUP_DELAY_SECONDS", "1800")), 60
)
PRODUCT_FOLLOWUP_POLL_SECONDS = max(
    int(os.environ.get("PRODUCT_FOLLOWUP_POLL_SECONDS", "30")), 10
)
PRODUCT_NEXT_DAY_DELAY_SECONDS = max(
    int(os.environ.get("PRODUCT_NEXT_DAY_DELAY_SECONDS", "86400")), 60
)
PRODUCT_FOLLOWUP_SATISFIED_ID = "product_followup_satisfied"
PRODUCT_FOLLOWUP_UNSATISFIED_ID = "product_followup_unsatisfied"
PRODUCT_RECOMMENDATION_KIND = "next_day_recommendation"
PRODUCT_FOLLOWUP_MESSAGE = (
    "مرحباً السادة! هل أنت راضٍ عن الردود من مساعدك الحصري، المتوفر على مدار الساعة "
    "طوال أيام الأسبوع فقط لك؟ 😊\n"
    "سأبقيك على اطلاع بأحدث العروض، وتوصيات المنتجات الرائجة، ومعلومات الطلبات في الوقت الفعلي.\n"
    "إذا كان لديك أي طلبات أخرى، فقط ناديني! أنا هنا من أجلك. 🛍️✨\n"
    "بعد محادثتنا وجدنا مجموعة خاصة"
)
PRODUCT_FOLLOWUP_SATISFIED_MESSAGE = (
    "شكراً جزيلاً لك! 😊 نحن سعداء جداً برضاك عن الخدمة 👍 إذا احتجت أي مساعدة إضافية أو استفسار، "
    "لا تتردد بالتواصل في أي وقت. يمكنك أيضاً زيارة قناتنا على واتساب والضغط على المتابعة "
    "للحصول على توصيات منتجات مخصصة لك 🛒✨\n\n"
    "اكتشف ما يناسبك الآن:\n"
    "https://whatsapp.com/channel/0029VaqFTglLikgDDe0D5E2D"
)
PRODUCT_FOLLOWUP_UNSATISFIED_MESSAGE = (
    "نعتذر إذا لم يكن الرد بالمستوى المطلوب 🙏\n"
    "اكتبي لنا ما الذي لم يكن واضحاً أو ما الذي تحتاجينه، وسنساعدك مباشرة."
)
PRODUCT_NEXT_DAY_MESSAGE_TEMPLATE = (
    "مرحبًا! 🎉 بعد محادثتنا، وجدنا لك مجموعة خاصة من {product_name} 🍅 "
    "التي تناسب كل احتياجاتك بأساليب وأشكال رائعة! لا تفوت فرصة الحصول على الأفضل "
    "لجعل مائدتك أكثر لذة وسحرًا! 🌟✨ اختَر الأفضل وامنح أطباقك نكهة لا تُنسى! 😋🍴\n\n"
    "انضم القناة الآن، آلاف المنتجات المختارة من أجلك:\n"
    "https://whatsapp.com/channel/0029VaqFTglLikgDDe0D5E2D"
)
followup_worker_lock = Lock()
followup_worker_started = False

def schedule_product_followup(phone_number, product_name=""):
    """جدولة تذكير واحد بعد رد متعلق بمنتج، مع استمرار الجدولة بعد إعادة التشغيل."""
    if phone_number and phone_number != OWNER_NUMBER:
        schedule_customer_followup(
            phone_number,
            product_name,
            PRODUCT_FOLLOWUP_DELAY_SECONDS,
        )

def send_product_followup(phone_number, product_name=""):
    """إرسال رسالة التذكير مع زري تقييم الرضا."""
    send_buttons(phone_number, PRODUCT_FOLLOWUP_MESSAGE, [
        {"id": PRODUCT_FOLLOWUP_SATISFIED_ID, "title": "👍 راضٍ"},
        {"id": PRODUCT_FOLLOWUP_UNSATISFIED_ID, "title": "👎 غير راضٍ"},
    ])

def send_next_day_recommendation(phone_number, product_name=""):
    """إرسال توصية اليوم التالي باسم المنتج الذي بحث عنه العميل."""
    send_message(
        phone_number,
        PRODUCT_NEXT_DAY_MESSAGE_TEMPLATE.format(product_name=product_name or "المنتجات المنزلية"),
    )

def product_followup_worker():
    """عامل خلفي يرسل التذكيرات المستحقة مرة واحدة فقط."""
    while True:
        try:
            for followup in get_due_customer_followups():
                if mark_customer_followup_sent(
                    followup["phone_number"], followup["due_at"]
                ):
                    if followup.get("followup_kind") == PRODUCT_RECOMMENDATION_KIND:
                        send_next_day_recommendation(
                            followup["phone_number"], followup.get("product_name", "")
                        )
                    else:
                        send_product_followup(
                            followup["phone_number"], followup.get("product_name", "")
                        )
        except Exception as exc:
            print(f"خطأ في عامل تذكير العملاء: {exc}")
        time.sleep(PRODUCT_FOLLOWUP_POLL_SECONDS)

def start_product_followup_worker():
    """تشغيل عامل التذكير مرة واحدة لكل عملية تشغيل."""
    global followup_worker_started
    with followup_worker_lock:
        if followup_worker_started:
            return
        Thread(target=product_followup_worker, daemon=True, name="product-followups").start()
        followup_worker_started = True

# ===== منع تكرار الرسائل =====
processed_messages = {}
DEDUP_WINDOW = 30
product_send_guard = {}
PRODUCT_SEND_WINDOW = 20

def restore_customer_session(sender):
    """استعادة حالة العميل من قاعدة البيانات عند أول رسالة بعد العودة."""
    if sender in user_states or sender in user_sessions:
        return
    saved = load_user_session(sender)
    if not saved:
        return
    saved_data = saved.get("data", {})
    if saved.get("state"):
        user_states[sender] = saved["state"]
    if saved_data:
        user_sessions[sender] = saved_data

def persist_customer_session(sender):
    """حفظ آخر حالة وسياق للعميل، أو حذفها بعد اكتمال/إلغاء الطلب."""
    state = user_states.get(sender)
    data = user_sessions.get(sender)
    if state or data:
        save_user_session(sender, state, data)
    else:
        delete_user_session(sender)

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

WELCOME_MESSAGE = f"👋 أهلاً بكِ في {BOT_NAME}\n\nكيف يمكنني مساعدتك اليوم؟\nهل تبحثين عن منتجات معينة، أم تودين الاستفسار عن طلباتك؟ 😊"
SHOPPING_ASSISTANT_MESSAGE = (
    "أهلاً بك! أنا مساعدك الذكي من Titiz، ويمكنني مساعدتك في القيام بالكثير من المهام التجارية، مثل:\n\n"
    "- *البحث عن المنتجات:* العثور على جميع الأدوات المنزلية والمنتجات بأسعار تنافسية.\n"
    "- *تحليل السوق:* اكتشاف أحدث الاتجاهات وتقييم فرص الربح لمنتجات معينة.\n"
    "- *دعم المندوبات:* الإجابة عن استفساراتك حول الطلبات، الشحن، وطرق الدفع.\n"
    "- *التصميم بالذكاء الاصطناعي:* مساعدتك في ابتكار تصاميم لمنتجاتك.\n\n"
    "ببساطة، أخبرني عما تبحث عنه وسأقوم بالباقي!"
)

# ===== تحميل الردود المخصصة من قاعدة البيانات =====
def load_custom_responses():
    """تحميل الردود المضافة من واتساب إلى النظام الموحد"""
    try:
        qas = load_qa()
        for keyword, answer in qas.items():
            add_response(keyword, answer, source="custom")
    except:
        pass

def sync_products_to_github():
    """دمج المنتجات المحلية مع نسخة GitHub ثم حفظها دون مسح المنتجات السابقة."""
    try:
        if not GITHUB_TOKEN:
            print("[GitHub] GITHUB_TOKEN غير موجود؛ تم إلغاء الحفظ الآمن.")
            return False

        remote_data, sha = github_load("products.json")
        products_dict = remote_data if isinstance(remote_data, dict) else {}
        products = get_all_products()
        for p in products:
            products_dict[p["name"]] = {
                "name": p["name"],
                "price": str(int(p["price"])),
                "description": p.get("description", ""),
                "keywords": p.get("keywords", ""),
                "image_id": p.get("image_id", "")
            }
        if not products_dict:
            print("[GitHub] تم منع كتابة products.json فارغاً فوق النسخة الحالية.")
            return False

        result = github_save("products.json", products_dict, sha=sha)
        if result:
            print(f"[GitHub] تم حفظ {len(products_dict)} منتج على GitHub")
        else:
            print("[GitHub] فشل حفظ المنتجات!")
    except Exception as e:
        print(f"[GitHub] خطأ في حفظ المنتجات: {e}")

def sync_qa_to_github():
    """حفظ الأسئلة والأجوبة على GitHub تلقائياً"""
    try:
        qas = load_qa()
        github_save("qa.json", qas)
    except:
        pass

def load_products_from_github():
    """تحميل المنتجات من GitHub عند بدء التشغيل"""
    try:
        data, sha = github_load("products.json")
        if data:
            count = 0
            existing = get_all_products()
            existing_names = [normalize_text(p["name"]) for p in existing]
            for name, info in data.items():
                if normalize_text(name) not in existing_names:
                    price = 0
                    try:
                        price = float(info.get("price", "0"))
                    except:
                        pass
                    desc = info.get("description", "")
                    image_id = info.get("image_id", "")
                    keywords = info.get("keywords", "")
                    if isinstance(keywords, list):
                        keywords = ",".join(keywords)
                    add_product(name, price, desc, image_id, 100, keywords)
                    count += 1
            print(f"[بدء التشغيل] تم تحميل {count} منتج من GitHub (إجمالي: {len(data)})")
        else:
            print("[بدء التشغيل] لا توجد منتجات على GitHub")
    except Exception as e:
        print(f"[بدء التشغيل] خطأ في تحميل المنتجات: {e}")

def load_qa_from_github():
    """تحميل الأسئلة والأجوبة من GitHub عند بدء التشغيل"""
    try:
        data, sha = github_load("qa.json")
        if data:
            existing_qa = load_qa()
            for keyword, answer in data.items():
                if keyword not in existing_qa:
                    save_qa(keyword, answer)
    except:
        pass

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
        print(f"[GitHub] GITHUB_TOKEN غير موجود! لا يمكن الحفظ.")
        return False
    try:
        url = f"{GITHUB_API}/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        content = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")
        payload = {"message": f"Update {filename}", "content": content}
        # لازم نجيب sha الحالي عشان نقدر نحدث الملف
        if not sha:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload["sha"] = resp.json().get("sha", "")
            elif resp.status_code == 404:
                pass  # ملف جديد
            else:
                print(f"[GitHub] خطأ في جلب sha: {resp.status_code} {resp.text[:100]}")
                return False
        else:
            payload["sha"] = sha
        resp = requests.put(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in [200, 201]:
            print(f"[GitHub] تم حفظ {filename} بنجاح")
            return True
        else:
            print(f"[GitHub] فشل حفظ {filename}: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[GitHub] خطأ: {e}")
        return False

def sync_customers_to_github():
    """دمج العملاء المحليين مع customers.json وحفظ نسخة واحدة لكل رقم هاتف."""
    try:
        if not GITHUB_TOKEN:
            print("[GitHub] GITHUB_TOKEN غير موجود؛ لم يتم حفظ العملاء.")
            return False

        remote_data, sha = github_load("customers.json")
        customers_by_phone = {}
        if isinstance(remote_data, dict):
            remote_records = remote_data.values()
        elif isinstance(remote_data, list):
            remote_records = remote_data
        else:
            remote_records = []

        for record in remote_records:
            if not isinstance(record, dict):
                continue
            phone = str(record.get("phone_number") or record.get("phone") or "").strip()
            if phone:
                customers_by_phone[phone] = record

        for customer in get_customers(limit=10000):
            phone = str(customer.get("phone_number") or "").strip()
            if not phone:
                continue
            customers_by_phone[phone] = {
                "phone_number": phone,
                "name": customer.get("name") or "",
                "address": customer.get("address") or "",
                "first_order_date": customer.get("first_order_date"),
                "order_count": int(customer.get("order_count") or 0),
                "created_at": customer.get("created_at"),
                "updated_at": customer.get("updated_at"),
            }

        if not customers_by_phone:
            print("[GitHub] لا يوجد عملاء للحفظ.")
            return False

        result = github_save("customers.json", customers_by_phone, sha=sha)
        if result:
            print(f"[GitHub] تم حفظ {len(customers_by_phone)} عميل دون تكرار على GitHub")
        return result
    except Exception as e:
        print(f"[GitHub] خطأ في حفظ العملاء: {e}")
        return False

def load_customers_from_github():
    """استعادة العملاء المحفوظين في customers.json إلى قاعدة البيانات المحلية."""
    try:
        data, _ = github_load("customers.json")
        if isinstance(data, dict):
            records = data.values()
        elif isinstance(data, list):
            records = data
        else:
            records = []

        restored = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            phone = str(record.get("phone_number") or record.get("phone") or "").strip()
            if phone:
                before = get_customer(phone)
                add_customer(phone, record.get("name") or None, record.get("address") or None)
                if before is None:
                    restored += 1
        print(f"[بدء التشغيل] تم استعادة {restored} عميل من customers.json")
    except Exception as e:
        print(f"[بدء التشغيل] خطأ في استعادة العملاء: {e}")

# تحميل البيانات بعد تعريف دوال GitHub، حتى لا يحدث استدعاء مبكر قبل github_load.
load_products_from_github()
load_customers_from_github()
load_qa_from_github()
load_custom_responses()

def send_message(to, text):
    return whatsapp.send_message(to, text)

def deliver_pending_replies(to):
    """إرسال ردود الإدارة المؤجلة بعد أن يبدأ العميل محادثته."""
    if not to or to == OWNER_NUMBER:
        return
    for pending in get_pending_replies(to):
        if send_message(to, pending["message"]):
            mark_pending_reply_sent(pending["id"])

def send_image(to, image_url, caption=""):
    return whatsapp.send_image(to, image_url, caption)

def send_image_by_id(to, media_id, caption=""):
    return whatsapp.send_image_by_id(to, media_id, caption)

def send_buttons(to, text, buttons):
    return whatsapp.send_buttons(to, text, buttons)

def send_welcome(to):
    """إرسال الترحيب الجديد مع أزرار الوصول السريع."""
    send_buttons(to, WELCOME_MESSAGE, [
        {"id": "browse_products", "title": "🛍️ المنتجات"},
        {"id": "menu_cart", "title": "🛒 السلة"},
        {"id": "menu_orders", "title": "📦 طلباتي"},
    ])

def send_product_card(to, product):
    """إرسال صورة المنتج وحدها ثم وصفه وأزراره بمعرفات لا تتكرر."""
    guard_key = (to, int(product.get("id", 0)))
    now = time.time()
    if now - product_send_guard.get(guard_key, 0) < PRODUCT_SEND_WINDOW:
        print(f"[تجاهل تكرار المنتج] {guard_key}")
        return False
    product_send_guard[guard_key] = now
    product_reply = format_product_card(product)
    image_id = product.get("image_id", "")
    if image_id:
        send_image_by_id(to, image_id)
    send_buttons(to, product_reply, [
        {"id": f"add_{product['id']}", "title": "🛒 إضافة للسلة"},
        {"id": f"det_{product['id']}", "title": "📋 تفاصيل المنتج"},
        {"id": "shopping_assistant", "title": "🔙 متابعة التسوق"},
    ])
    schedule_product_followup(to, product.get("name", ""))

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
    if images:
        schedule_product_followup(to, response_data.get("original_keyword", ""))

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
            {"id": "browse_products", "title": "🛍️ تصفح المنتجات", "description": "عرض جميع المنتجات"},
            {"id": "menu_search", "title": "🔍 البحث عن منتج", "description": "اكتبي اسم المنتج"},
            {"id": "menu_cart", "title": "🛒 السلة", "description": "عرض سلة المشتريات"},
            {"id": "menu_orders", "title": "📦 طلباتي", "description": "متابعة طلباتك"},
            {"id": "menu_track", "title": "🚚 تتبع الطلب", "description": "عرض آخر حالة"},
            {"id": "menu_payment", "title": "💳 طرق الدفع", "description": "حسابات التحويل"},
            {"id": "menu_location", "title": "📍 مواقعنا", "description": "عناوين الفروع"},
            {"id": "menu_contact", "title": "📞 التواصل معنا", "description": "للاستفسارات"}
        ]
    }]
    send_list(to, "🏠 *أهلاً بكِ في Titiz!*\n\nاختاري من القائمة:", "📋 القائمة", sections)

ORDER_STATUSES = [
    "بانتظار مراجعة الدفع", "تم الدفع", "جديد", "جاري التجهيز",
    "تم الشحن", "تم التسليم", "ملغي"
]
PAYMENT_COD = "الدفع عند الاستلام"
PAYMENT_TRANSFER = "التحويل المسبق"
TRANSFER_PAYMENT_METHODS = {PAYMENT_TRANSFER, "تحويل مسبق"}
PAYMENT_CONFIRMATION_MESSAGE = "تم استلام دفعتك بنجاح وسيتم تجهيز طلبك قريبًا."

def normalize_order_number(value):
    """توحيد رقم الطلب سواء أُرسل مع ORD- أو بدونه."""
    value = (value or "").strip().upper()
    if not value.startswith("ORD-"):
        value = f"ORD-{value.zfill(6)}"
    return value

def format_order_for_admin(order):
    """تنسيق شامل لطلب الإدارة."""
    lines = [
        f"📦 *تفاصيل الطلب: {order.get('order_number', 'غير محدد')}*",
        f"👤 العميل: {order.get('customer_name') or 'غير محدد'}",
        f"📱 الهاتف: {order.get('phone_number') or 'غير محدد'}",
        f"📍 العنوان: {order.get('address') or 'غير محدد'}",
        f"💳 طريقة الدفع: {order.get('payment_method') or 'غير محددة'}",
        f"📊 الحالة: {order.get('order_status') or 'جديد'}",
        f"🕐 التاريخ: {order.get('created_at') or 'غير محدد'}",
        "",
        "🛍️ *المنتجات:*"
    ]
    for item in order.get("products_data", []) or []:
        quantity = item.get("quantity", item.get("qty", 1))
        price = float(item.get("price", 0) or 0)
        lines.append(f"• {item.get('name', 'منتج')} × {quantity} = {int(price * int(quantity))} ريال")
    lines.append(f"\n💰 *الإجمالي: {int(float(order.get('total_price', 0) or 0))} ريال*")
    if order.get("payment_proof_url"):
        lines.append("📸 إشعار التحويل: مرفق بالطلب")
    return "\n".join(lines)

def send_customer_orders(to):
    """عرض طلبات العميل مع الحالة الحالية وزر تحديث الحالة."""
    orders = get_customer_orders(to)
    if not orders:
        send_message(to, "📦 لا توجد طلبات مسجلة على رقمك حالياً.")
        return
    text = "📦 *طلباتك الحالية:*\n\n"
    for order in orders:
        text += (
            f"📋 *{order['order_number']}*\n"
            f"الحالة: *{order.get('order_status') or 'جديد'}*\n"
            f"الإجمالي: {int(float(order.get('total_price', 0) or 0))} ريال\n"
            f"التاريخ: {order.get('created_at') or 'غير محدد'}\n\n"
        )
    send_message(to, text.rstrip())
    send_buttons(to, "يمكنك تحديث القائمة في أي وقت:", [
        {"id": "menu_orders", "title": "🔄 تحديث الحالة"},
        {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
        {"id": "menu_cart", "title": "🛒 السلة"},
    ])

def send_cart_view(to):
    """عرض السلة مع إجراءات تفاعلية لكل منتج."""
    cart_items = get_cart(to)
    if not cart_items:
        send_message(to, "🛒 السلة فارغة!\n\nأضيفي منتجاً أولاً 😊")
        send_buttons(to, "اختاري ما تريدين:", [
            {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
            {"id": "menu_orders", "title": "📦 طلباتي"},
        ])
        return

    total = 0
    lines = ["🛒 *سلة المشتريات:*", ""]
    action_rows = []
    for item in cart_items:
        item_total = item["price"] * item["quantity"]
        total += item_total
        lines.append(f"• {item['name']} × {item['quantity']} = {int(item_total)} ريال")
        action_rows.extend([
            {"id": f"inc_{item['product_id']}", "title": f"➕ {item['name'][:17]}", "description": "زيادة الكمية"},
            {"id": f"dec_{item['product_id']}", "title": f"➖ {item['name'][:17]}", "description": "إنقاص الكمية"},
            {"id": f"del_{item['product_id']}", "title": f"❌ حذف {item['name'][:15]}", "description": "حذف المنتج من السلة"},
        ])
    lines.extend(["", f"💰 *الإجمالي: {int(total)} ريال*", "🚚 التوصيل: مجاني"])
    send_message(to, "\n".join(lines))
    send_list(to, "اختاري إجراءً للسلة:", "إدارة السلة", [{
        "title": "المنتجات",
        "rows": action_rows[:10]
    }])
    send_buttons(to, "جاهزة لإكمال الطلب؟", [
        {"id": "checkout", "title": "✅ إكمال الطلب"},
        {"id": "clear_cart", "title": "🗑️ تفريغ السلة"},
        {"id": "shopping_assistant", "title": "🔙 متابعة التسوق"},
    ])

def send_payment_choice(to):
    """إرسال طرق الدفع مرة واحدة في كل انتقال واضح إلى الدفع."""
    payment_text = (
        "💳 *طرق الدفع:*\n\n"
        "✅ *الدفع عند الاستلام:*\n"
        "نحط المنتج لأقرب نقطة منكِ وتدفعي وقت الاستلام 👌\n\n"
        "✅ *التحويل المسبق:*\n"
        "تدفعي وإحنا نوصل لكِ الطلب لباب بيتكِ 🚚\n\n"
        "💰 *حسابات التحويل:*\n\n"
        "🟢 *نقطة جيب:* 906072\n"
        "🟡 *الكريمي نقطة حاسب:* 1202686\n"
        "🏦 *إيداع عبر الكريمي:* 3122678098\n\n"
        "اختاري الطريقة اللي تناسبكِ 😊"
    )
    send_buttons(to, payment_text, [
        {"id": "pay_cod", "title": "💵 الدفع عند الاستلام"},
        {"id": "pay_transfer", "title": "💳 التحويل المسبق"},
        {"id": "cancel_checkout", "title": "❌ إلغاء الطلب"},
    ])

def send_contact_menu(to):
    """عرض خيارات التواصل بطريقة تفاعلية."""
    send_list(to, "📞 اختاري طريقة التواصل:", "التواصل", [{
        "title": "خدمة العملاء",
        "rows": [
            {"id": "contact_call", "title": "📞 اتصال", "description": "اتصلي بخدمة العملاء"},
            {"id": "contact_whatsapp", "title": "💬 واتساب", "description": "محادثة خدمة العملاء"},
            {"id": "contact_location", "title": "📍 موقعنا", "description": "فروع Titiz"},
            {"id": "contact_hours", "title": "⏰ أوقات العمل", "description": "مواعيد الخدمة"},
        ]
    }])


# ╔══════════════════════════════════════════════════════════════╗
# ║                 معالجة أوامر المالك                          ║
# ╚══════════════════════════════════════════════════════════════╝

def handle_owner_command(sender, msg_body, msg_normalized, message):
    """معالجة أوامر المالك - ترجع True إذا تم التعامل مع الأمر"""

    # إذا كان رقم الإدارة يختبر دورة شراء، فصورة التحويل ليست صورة منتج.
    # نعيدها لمسار العميل حتى تُحفظ كإثبات دفع، حتى بعد استعادة الجلسة من SQLite.
    restore_customer_session(sender)
    if (
        message.get("type") == "image"
        and user_states.get(sender) == "awaiting_transfer_proof"
    ):
        return False

    # === رد على زبون ===
    reply_match = re.match(r"^\s*رد\s+([+]?\d{7,15})\s+([\s\S]+?)\s*$", msg_body or "")
    if msg_normalized == "رد" or msg_normalized.startswith("رد "):
        if not reply_match:
            send_message(OWNER_NUMBER, "❌ الصيغة الصحيحة: رد [رقم العميل] [الرسالة كاملة]")
            return True

        target_phone = reply_match.group(1).lstrip("+")
        reply_text = reply_match.group(2).strip()
        if not reply_text:
            send_message(OWNER_NUMBER, "❌ اكتب نص الرسالة بعد رقم العميل.")
            return True

        if has_contact(target_phone) or get_customer(target_phone):
            sent = send_message(target_phone, reply_text)
            if sent:
                send_message(OWNER_NUMBER, f"✅ تم إرسال الرد كاملاً إلى العميل {target_phone}")
            else:
                send_message(OWNER_NUMBER, f"⚠️ تعذر إرسال الرد إلى {target_phone}. تأكد من الرقم أو نافذة المحادثة.")
        elif queue_pending_reply(target_phone, reply_text):
            send_message(
                OWNER_NUMBER,
                f"✅ تم حفظ الرد للعميل {target_phone}، وسيتم إرساله تلقائياً عندما يراسل البوت.\n\n💬 الرد المحفوظ: {reply_text}",
            )
        else:
            send_message(OWNER_NUMBER, "❌ تعذر حفظ الرد المؤجل.")
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
                # حفظ على GitHub
                sync_qa_to_github()
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
        # حفظ على GitHub
        sync_qa_to_github()
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
                saved = sync_products_to_github()
                if saved:
                    send_message(OWNER_NUMBER, f"✅ تم إضافة وحفظ المنتج دائمًا على GitHub:\n📦 {product_name}\n💰 {int(price_val)} ريال\n📝 {product_desc}\n🔑 كلمات: {keywords_str or 'لا يوجد'}\n\nلإضافة صورة: أرسل صورة مع كابشن فيه اسم المنتج")
                else:
                    send_message(OWNER_NUMBER, f"⚠️ تم إضافة المنتج محلياً، لكن *فشل حفظه على GitHub* (تأكد من GITHUB_TOKEN):\n📦 {product_name}\n💰 {int(price_val)} ريال")
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
            sync_products_to_github()
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
            sync_products_to_github()
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

    # === البحث عن عميل ===
    if msg_normalized.startswith("بحث "):
        query = msg_body.split(" ", 1)[1].strip()
        customers = search_customers(query)
        if customers:
            text = f"🔎 *نتائج البحث عن: {query}*\n\n"
            for customer in customers:
                text += (
                    f"👤 {customer.get('name') or 'بدون اسم'}\n"
                    f"📱 {customer.get('phone_number')}\n"
                    f"📍 {customer.get('address') or 'بدون عنوان'}\n"
                    f"📦 الطلبات: {customer.get('order_count', 0)}\n\n"
                )
            send_message(OWNER_NUMBER, text.rstrip())
        else:
            send_message(OWNER_NUMBER, f"❌ لم أجد عميلاً يطابق: {query}")
        return True

    # === بيانات عميل ===
    if msg_normalized.startswith("عميل "):
        query = msg_body.split(" ", 1)[1].strip()
        customer = get_customer(query)
        if not customer:
            results = search_customers(query, limit=1)
            customer = results[0] if results else None
        if customer:
            send_message(OWNER_NUMBER,
                f"👤 *بيانات العميل*\n\n"
                f"الاسم: {customer.get('name') or 'غير مسجل'}\n"
                f"📱 الهاتف: {customer.get('phone_number')}\n"
                f"📍 العنوان: {customer.get('address') or 'غير مسجل'}\n"
                f"🗓️ أول طلب: {customer.get('first_order_date') or 'لا يوجد'}\n"
                f"📦 عدد الطلبات: {customer.get('order_count', 0)}")
        else:
            send_message(OWNER_NUMBER, f"❌ لم أجد العميل: {query}")
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

    # === الطلبات الجديدة ===
    if msg_normalized in ["طلبات جديدة", "طلبات الجديده", "الجديد"]:
        orders = get_orders(status="جديد", limit=30)
        if orders:
            text = "🆕 *الطلبات الجديدة:*\n\n" + "\n".join(
                f"📦 {o['order_number']} | {o.get('customer_name') or 'بدون اسم'} | {int(float(o.get('total_price', 0) or 0))} ريال"
                for o in orders
            )
            send_message(OWNER_NUMBER, text)
        else:
            send_message(OWNER_NUMBER, "✅ لا توجد طلبات جديدة حالياً")
        return True

    # === الطلبات ===
    if msg_normalized in ["طلبات"]:
        orders = get_orders(limit=20)
        if orders:
            orders_list = "📋 *آخر الطلبات:*\n\n"
            for o in orders:
                orders_list += f"📦 *{o['order_number']}* | {o.get('customer_name') or 'بدون اسم'} | {o.get('order_status') or 'جديد'} | {int(float(o.get('total_price', 0) or 0))} ريال\n"
            send_message(OWNER_NUMBER, orders_list)
        else:
            send_message(OWNER_NUMBER, "📋 لا توجد طلبات")
        return True

    # === تفاصيل طلب ===
    if msg_normalized.startswith("تفاصيل "):
        order_number = normalize_order_number(msg_body.split(" ", 1)[1])
        order = get_order(order_number)
        send_message(OWNER_NUMBER, format_order_for_admin(order) if order else f"❌ لم أجد الطلب: {order_number}")
        return True

    # === تأكيد دفع حوالة ===
    if msg_normalized.startswith("تأكيد دفع ") or msg_normalized.startswith("تأكيد الدفع "):
        order_text = msg_body.split(" ", 2)[-1].strip()
        order_number = normalize_order_number(order_text)
        order = get_order(order_number)
        if not order:
            send_message(OWNER_NUMBER, f"❌ لم أجد الطلب: {order_number}")
        elif order.get("payment_method") not in TRANSFER_PAYMENT_METHODS:
            send_message(OWNER_NUMBER, "❌ هذا الطلب ليس بتحويل مسبق.")
        elif not order.get("payment_proof_url"):
            send_message(OWNER_NUMBER, "❌ لا يمكن تأكيد الدفع قبل حفظ صورة إشعار التحويل مع الطلب.")
        else:
            updated = update_order_status(order_number, "تم الدفع")
            if updated and order.get("phone_number"):
                send_message(order["phone_number"], PAYMENT_CONFIRMATION_MESSAGE)
            if updated:
                send_message(OWNER_NUMBER, f"✅ تم تأكيد الدفع للطلب {order_number} وإشعار العميل.")
            else:
                send_message(OWNER_NUMBER, f"❌ تعذر تحديث حالة الطلب {order_number}.")
        return True

    # === تغيير حالة طلب ===
    if msg_normalized.startswith("حاله ") or msg_normalized.startswith("حالة "):
        parts = msg_body.split(" ", 2)
        if len(parts) >= 3:
            order_num = normalize_order_number(parts[1])
            new_status = parts[2].strip()
            if new_status not in ORDER_STATUSES:
                send_message(OWNER_NUMBER, "❌ الحالة غير صحيحة. الحالات المتاحة:\n" + "، ".join(ORDER_STATUSES))
            else:
                update_order_status(order_num, new_status)
                order = get_order(order_num)
                if order and order.get("phone_number"):
                    send_message(order["phone_number"], f"🔔 تحديث طلبك *{order_num}*\nالحالة الحالية: *{new_status}*")
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
        help_text += "• عملاء / زبائن\n"
        help_text += "• عميل [رقم أو اسم]\n"
        help_text += "• بحث [اسم أو رقم]\n"
        help_text += "• طلبات\n"
        help_text += "• طلبات جديدة\n"
        help_text += "• تفاصيل [رقم الطلب]\n"
        help_text += "• حالة [رقم] [الحالة]\n"
        help_text += "• تأكيد دفع [رقم الطلب]\n"
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
            sync_products_to_github()
        elif media_id and not caption:
            send_message(OWNER_NUMBER, "❌ أرسل الصورة مع كابشن فيه اسم المنتج")
        return True

    return False


# ╔══════════════════════════════════════════════════════════════╗
# ║                 معالجة رسائل العملاء                         ║
# ╚══════════════════════════════════════════════════════════════╝

def handle_customer_message(sender, msg_body, msg_normalized, message):
    """معالجة رسائل العملاء"""
    restore_customer_session(sender)
    state = user_states.get(sender, "")
    raw_action = (msg_body or "").strip().lower()

    # أي رسالة جديدة تعني أن العميل عاد للمحادثة؛ نلغي التذكير السابق.
    if raw_action not in {
        PRODUCT_FOLLOWUP_SATISFIED_ID,
        PRODUCT_FOLLOWUP_UNSATISFIED_ID,
    }:
        cancel_customer_followup(sender)

    if raw_action == PRODUCT_FOLLOWUP_SATISFIED_ID:
        send_message(sender, PRODUCT_FOLLOWUP_SATISFIED_MESSAGE)
        followup = get_customer_followup(sender) or {}
        schedule_customer_followup(
            sender,
            followup.get("product_name", ""),
            PRODUCT_NEXT_DAY_DELAY_SECONDS,
            PRODUCT_RECOMMENDATION_KIND,
        )
        return

    if raw_action == PRODUCT_FOLLOWUP_UNSATISFIED_ID:
        cancel_customer_followup(sender)
        send_message(sender, PRODUCT_FOLLOWUP_UNSATISFIED_MESSAGE)
        return

    # أزرار المنتج: نستخدم النص الخام لأن normalize_text يزيل الشرطة السفلية.
    if raw_action.startswith("add_"):
        try:
            product = get_product(int(raw_action.split("_", 1)[1]))
        except (ValueError, IndexError):
            product = None
        if product:
            add_to_cart(sender, product["id"], 1)
            send_message(sender, f"✅ تم إضافة *{product['name']}* إلى السلة")
            send_buttons(sender, "ماذا تريدين الآن؟", [
                {"id": "menu_cart", "title": "🛒 عرض السلة"},
                {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
            ])
        else:
            send_message(sender, "❌ لم أتمكن من العثور على هذا المنتج، جربي القائمة مرة أخرى.")
        return

    if raw_action.startswith("det_"):
        try:
            product = get_product(int(raw_action.split("_", 1)[1]))
        except (ValueError, IndexError):
            product = None
        if product:
            send_message(sender, f"📋 *تفاصيل المنتج*\n\n{product.get('description') or 'لا يوجد وصف إضافي.'}")
            send_buttons(sender, "اختاري الإجراء المناسب:", [
                {"id": f"add_{product['id']}", "title": "🛒 إضافة للسلة"},
                {"id": "menu_cart", "title": "🛍️ عرض السلة"},
            ])
            schedule_product_followup(sender, product.get("name", ""))
        else:
            send_message(sender, "❌ تفاصيل المنتج غير متاحة حالياً.")
        return

    if raw_action == "menu_cart":
        send_cart_view(sender)
        return

    if raw_action == "shopping_assistant":
        send_message(sender, SHOPPING_ASSISTANT_MESSAGE)
        return

    if raw_action == "menu_search":
        send_message(sender, "🔍 اكتبي اسم المنتج أو صفيه بكلماتك، وسأبحث لكِ عنه 😊")
        return

    if raw_action == "menu_track":
        send_customer_orders(sender)
        return

    if raw_action.startswith(("inc_", "dec_", "del_")):
        try:
            action, product_id_text = raw_action.split("_", 1)
            product_id = int(product_id_text)
            cart_item = next((item for item in get_cart(sender) if item["product_id"] == product_id), None)
        except (ValueError, IndexError):
            action, cart_item = "", None
        if not cart_item:
            send_message(sender, "❌ هذا المنتج غير موجود في السلة.")
        elif action == "inc":
            update_cart_quantity(sender, product_id, cart_item["quantity"] + 1)
            send_cart_view(sender)
        elif action == "dec":
            update_cart_quantity(sender, product_id, cart_item["quantity"] - 1)
            send_cart_view(sender)
        else:
            remove_from_cart(sender, product_id)
            send_cart_view(sender)
        return

    if raw_action == "clear_cart":
        clear_cart(sender)
        send_message(sender, "🗑️ تم تفريغ السلة ✅")
        send_buttons(sender, "اختاري ما تريدين:", [
            {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
            {"id": "menu_orders", "title": "📦 طلباتي"},
        ])
        return

    if raw_action == "cancel_checkout":
        user_states.pop(sender, None)
        user_sessions.pop(sender, None)
        send_message(sender, "❌ تم إلغاء إتمام الطلب. السلة ما زالت محفوظة ويمكنك المتابعة لاحقاً.")
        return

    # === حالات الجلسة ===

    if state == "awaiting_name":
        customer_name = msg_body.strip()
        add_customer(sender, customer_name)
        customers_saved = sync_customers_to_github()
        user_states[sender] = "awaiting_address"
        user_sessions[sender] = {"name": customer_name}
        if customers_saved:
            send_message(sender, "حياك الله 🌟\nأهلاً بك في Titiz\nتم حفظ بياناتك بنجاح\nلو احتجت اي أداة منزلية ارسل اسم المنتج")
        else:
            send_message(sender, "⚠️ تعذر حفظ بياناتك على GitHub حالياً، لكن سنكمل طلبك. يرجى إبلاغ الإدارة إذا تكرر الخطأ.")
        send_message(sender, "📍 تمام! الحين أرسلي لنا عنوان التوصيل (المنطقة أو أقرب نقطة) 😊\n📦 وين تحبين نحط لكِ المنتج؟ 🤔\n\nنقدر نحطه في أي مكان قريب منكِ:\n\n🏪 محل قريب من بيتكِ\n🛍️ بقالة في حارتكِ\n📍 أي نقطة تحدديها\n\nأرسلي لنا اسم المكان أو المنطقة وإحنا نوصله لأقرب نقطة منكِ 😊👌")
        return

    if state == "awaiting_customer_confirmation":
        if raw_action == "confirm_info" or msg_normalized in ["نعم", "صحيح", "صحيحه"]:
            user_states[sender] = "awaiting_payment"
            send_payment_choice(sender)
        elif raw_action == "change_info" or "تعديل" in msg_normalized:
            user_states[sender] = "awaiting_name"
            send_message(sender, "👤 أرسلي الاسم الصحيح من فضلكِ 😊")
        else:
            send_buttons(sender, "هل البيانات صحيحة؟", [
                {"id": "confirm_info", "title": "✅ نعم، صحيحة"},
                {"id": "change_info", "title": "✏️ تعديل البيانات"},
                {"id": "cancel_checkout", "title": "❌ إلغاء"},
            ])
        return

    if state == "awaiting_address":
        session_data = user_sessions.get(sender, {})
        session_data["address"] = msg_body.strip()
        user_sessions[sender] = session_data
        add_customer(sender, session_data.get("name"), session_data["address"])
        sync_customers_to_github()
        user_states[sender] = "awaiting_payment"
        send_payment_choice(sender)
        return

    if state == "awaiting_payment":
        session_data = user_sessions.get(sender, {})
        if "استلام" in msg_normalized or raw_action in {"pay_cod", "1"}:
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
        elif "تحويل" in msg_normalized or "مسبق" in msg_normalized or raw_action in {"pay_transfer", "2"}:
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
                proof_id = message.get("image", {}).get("id", "")
                if not proof_id:
                    send_message(sender, "⚠️ لم أتمكن من قراءة صورة إشعار التحويل. أرسلي الصورة مرة أخرى من فضلكِ.")
                    return
                order_number, _ = create_order(customer["id"], items, total, PAYMENT_TRANSFER)
                proof_saved = update_order_payment_proof(order_number, proof_id)
                if not proof_saved:
                    send_message(sender, "⚠️ تعذر حفظ صورة إشعار التحويل مع الطلب. أرسلي الصورة مرة أخرى من فضلكِ.")
                    return
                clear_cart(sender)
                user_states.pop(sender, None)
                user_sessions.pop(sender, None)
                send_message(sender, f"✅ *تم استلام طلبك!*\n\n📋 رقم الطلب: *{order_number}*\n💰 الإجمالي: {int(total)} ريال\n💳 الدفع: {PAYMENT_TRANSFER}\n\n⏳ الحالة: *بانتظار مراجعة الدفع*\nسنؤكد لكِ خلال دقائق 😊")
                notify_owner_new_order(order_number, sender, name, address, items, total, PAYMENT_TRANSFER)
                send_message(OWNER_NUMBER, f"📸 *صورة إشعار التحويل للطلب {order_number}*\nمن العميل: {name or sender}\n📊 الحالة: *بانتظار مراجعة الدفع*")
                send_image_by_id(OWNER_NUMBER, proof_id, f"إشعار التحويل — {order_number}")
            else:
                user_states.pop(sender, None)
                send_message(sender, "❌ السلة فارغة!")
            return
        else:
            send_message(sender, "📸 أرسلي صورة إشعار التحويل من فضلكِ 😊")
            return

    if state == "product_context":
        context = user_sessions.get(sender, {})
        last_product = context.get("last_product") if isinstance(context, dict) else None
        if last_product:
            if raw_action in {"add", "اضف", "أضف", "إضافة", "طلب", "شراء"}:
                add_to_cart(sender, last_product["id"], 1)
                send_message(sender, f"✅ تم إضافة *{last_product['name']}* إلى السلة")
                return
            if any(word in msg_normalized for word in ["سعر", "بكم", "تفاصيل", "وصف"]):
                send_message(sender, format_product_card(last_product))
                schedule_product_followup(sender, last_product.get("name", ""))
                return

    # اختيار من قائمة منتجات
    if state == "product_list" and msg_normalized.isdigit():
        choice = int(msg_normalized)
        products_list = user_sessions.get(sender, [])
        if isinstance(products_list, list) and 1 <= choice <= len(products_list):
            found = products_list[choice - 1]
            user_states[sender] = "product_context"
            user_sessions[sender] = {"last_product": found}
            send_product_card(sender, found)
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
        send_cart_view(sender)
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
            user_states[sender] = "awaiting_customer_confirmation"
            send_buttons(sender, f"👤 الاسم: {customer['name']}\n📍 العنوان: {customer.get('address','غير محدد')}\n\nهل البيانات صحيحة؟",
                [{"id": "confirm_info", "title": "✅ نعم، صحيحة"},
                 {"id": "change_info", "title": "✏️ تعديل البيانات"},
                 {"id": "cancel_checkout", "title": "❌ إلغاء"}])
        else:
            user_states[sender] = "awaiting_name"
            send_message(sender, "👤 ايش اسمكِ الكريم؟ 😊")
        return

    if raw_action == "change_info" or msg_normalized == "changeinfo":
        user_states[sender] = "awaiting_name"
        send_message(sender, "👤 ايش اسمكِ الكريم؟ 😊")
        return

    # طلباتي
    if raw_action == "menu_orders" or msg_normalized in [normalize_text("طلباتي"), normalize_text("menu_orders")]:
        send_customer_orders(sender)
        return

    if msg_normalized in [normalize_text("تتبع الطلب"), normalize_text("تتبع"), "track"]:
        send_customer_orders(sender)
        return

    if raw_action == "contact_call":
        send_message(sender, "📞 يمكنك الاتصال بخدمة العملاء على: 777355955")
        return
    if raw_action == "contact_whatsapp":
        send_message(sender, "💬 اكتبي رسالتك هنا، وموظفة Titiz ستساعدكِ فوراً.")
        return
    if raw_action == "contact_location":
        send_message(sender, "📍 فروعنا:\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم")
        return
    if raw_action == "contact_hours":
        send_message(sender, "⏰ أوقات العمل: يومياً من 8 صباحاً حتى 10 مساءً، وموظفتنا الذكية متاحة 24 ساعة.")
        return

    # أزرار القائمة التفاعلية
    if raw_action == "shopping_assistant" or raw_action == "menu_products" or msg_normalized == "menuproducts":
        send_message(sender, SHOPPING_ASSISTANT_MESSAGE)
        return

    if raw_action == "browse_products" or msg_normalized == "browseproducts":
        send_message(sender, "✍️ اكتبي اسم المنتج الذي تبحثين عنه 😊\n\nمثلاً: قدور، فرامة، أو ثلاجة شاي")
        return
    if raw_action == "menu_payment" or msg_normalized == "menupayment":
        send_message(sender, "💳 *طرق الدفع المتاحة:*\n\n✅ الدفع عند الاستلام\nنحط الطلب لأقرب نقطة منك وتدفعي وقت الاستلام.\n\n✅ التحويل المسبق\nتدفعي أولاً ثم يتم توصيل الطلب لباب المنزل.\n\n💰 حسابات التحويل:\n🟢 نقطة جيب: 906072\n🟡 الكريمي نقطة حاسب: 1202686\n🏦 إيداع عبر الكريمي: 3122678098")
        return
    if raw_action == "menu_location" or msg_normalized == "menulocation":
        resp = find_response(normalize_text("الموقع"))
        if resp:
            send_response(sender, resp)
        return
    if raw_action == "menu_contact" or msg_normalized == "menucontact":
        send_contact_menu(sender)
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
        send_product_card(sender, found)
        return
    elif len(matching) > 1:
        send_message(sender, "🔍 وجدنا لكِ هذه المنتجات، اختاري الزر تحت المنتج المناسب:")
        for product in matching[:10]:
            send_product_card(sender, product)
        return

    # === رد افتراضي (آخر شي بعد كل البحث) ===
    send_welcome(sender)


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

        record_contact(sender)

        # Mark as Read (صحين أخضر)
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

        # جاري الكتابة (Typing Indicator)
        whatsapp.send_typing_indicator(message_id)
        time.sleep(2)

        # لا نحفظ العميل عند أول رسالة؛ يتم الحفظ بعد إدخال الاسم فقط.

        # إشعار المالك
        if sender != OWNER_NUMBER and msg_body:
            notify_owner(sender, msg_body)

        # معالجة أوامر المالك
        if sender == OWNER_NUMBER:
            if handle_owner_command(sender, msg_body, msg_normalized, message):
                return jsonify({"status": "ok"}), 200

        # معالجة رسائل العملاء (والمالك للاختبار)
        try:
            deliver_pending_replies(sender)
            handle_customer_message(sender, msg_body, msg_normalized, message)
        finally:
            persist_customer_session(sender)

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

start_product_followup_worker()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
