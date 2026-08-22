"""
بوت Titiz الذكي - نسخة موحدة
تطبيق WhatsApp Bot متقدم لمتجر Titiz
نظام ردود موحد: كل الردود (المبرمجة والمضافة من واتساب) تُعامل بنفس الطريقة
"""

from flask import Flask, request, jsonify, make_response
import requests
import json
import os
import re
import base64
import difflib
import hashlib
import io
import hmac
import sqlite3
from datetime import datetime
import time
import unicodedata
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from urllib.parse import quote
from zoneinfo import ZoneInfo
from PIL import Image, ImageOps
import asyncio
import edge_tts

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
    get_pending_replies, mark_pending_reply_sent, update_product_metadata,
    update_product_fields,
    claim_processed_webhook_message, record_message_event, update_message_event,
    get_message_events, reserve_owner_notification_sequence,
    db_lock, DB_PATH, set_order_sync_callback,
)
from whatsapp_api import WhatsAppAPI, format_product_card, parse_product_price

app = Flask(__name__)

# ===== الإعدادات العامة =====
BOT_NAME = "Titiz موظفتك الذكية، نرد على جميع طلباتكم 24 ساعة"

# ===== بيانات WhatsApp =====
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "").strip()
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "").strip()
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "bot_adawat_manziliya_2026")
APP_SECRET = os.environ.get("APP_SECRET", "").strip()
OWNER_NUMBER = os.environ.get("OWNER_NUMBER", "967773595571")
YEMEN_TIMEZONE = ZoneInfo("Asia/Aden")

# ===== بيانات GitHub =====
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "ahobyuplmned2-bit/titiz-bot"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

# ===== الصوت والفهم الذكي =====
# يمكن استخدام OpenAI مباشرة أو أي خدمة متوافقة مع واجهتي audio/transcriptions و chat/completions.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
VOICE_TRANSCRIPTION_API_KEY = os.environ.get("VOICE_TRANSCRIPTION_API_KEY", OPENAI_API_KEY)
VOICE_TRANSCRIPTION_API_BASE = os.environ.get(
    "VOICE_TRANSCRIPTION_API_BASE", OPENAI_API_BASE
).rstrip("/")
VOICE_TRANSCRIPTION_MODEL = os.environ.get("VOICE_TRANSCRIPTION_MODEL", "whisper-1")
SMART_AI_API_KEY = os.environ.get("SMART_AI_API_KEY", OPENAI_API_KEY)
SMART_AI_API_BASE = os.environ.get("SMART_AI_API_BASE", OPENAI_API_BASE).rstrip("/")
SMART_AI_MODEL = os.environ.get("SMART_AI_MODEL", "gpt-5-mini")
VOICE_MAX_RETRIES = max(int(os.environ.get("VOICE_MAX_RETRIES", "3")), 1)
VOICE_RETRY_BASE_SECONDS = max(float(os.environ.get("VOICE_RETRY_BASE_SECONDS", "2")), 1.0)
VOICE_DEDUP_SECONDS = max(int(os.environ.get("VOICE_DEDUP_SECONDS", "120")), 30)
VOICE_REPLY_ENABLED = os.environ.get("VOICE_REPLY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
VOICE_REPLY_VOICE = os.environ.get("VOICE_REPLY_VOICE", "ar-YE-MaryamNeural").strip() or "ar-YE-MaryamNeural"
VOICE_REPLY_MAX_CHARS = max(int(os.environ.get("VOICE_REPLY_MAX_CHARS", "480")), 120)
IMAGE_MAX_RETRIES = max(int(os.environ.get("IMAGE_MAX_RETRIES", "1")), 1)
IMAGE_RETRY_BASE_SECONDS = max(float(os.environ.get("IMAGE_RETRY_BASE_SECONDS", "1")), 0.2)
IMAGE_REQUEST_TIMEOUT = max(float(os.environ.get("IMAGE_REQUEST_TIMEOUT", "25")), 5.0)
CATALOG_IMAGE_TIMEOUT = max(float(os.environ.get("CATALOG_IMAGE_TIMEOUT", "4")), 2.0)
CATALOG_IMAGE_MATCH_THRESHOLD = max(float(os.environ.get("CATALOG_IMAGE_MATCH_THRESHOLD", "0.88")), 0.7)
CATALOG_IMAGE_FAMILY_THRESHOLD = max(float(os.environ.get("CATALOG_IMAGE_FAMILY_THRESHOLD", "0.74")), 0.65)
catalog_image_fingerprint_cache = {}

# ===== تهيئة الخدمات =====
whatsapp = WhatsAppAPI(ACCESS_TOKEN, PHONE_NUMBER_ID)
init_db()

# ===== متغيرات الجلسات =====
user_sessions = {}
user_states = {}
active_message_events = {}
voice_processing_lock = Lock()
voice_recent_media = {}
voice_reply_mode = ContextVar("voice_reply_mode", default=False)
voice_reply_sent = ContextVar("voice_reply_sent", default=False)
SEMANTIC_INTENTS = {
    "product_search", "product_purchase", "price_inquiry", "orders", "cart", "payment",
    "offers", "discount", "complaint", "greeting", "clarification", "general", "social_chat",
    "affirmation", "rejection", "product_choice", "quantity_change", "comparison", "budget",
    "agent_handoff", "stop_reminder", "shipping", "location", "warranty", "catalog", "out_of_scope",
}

# ===== تذكير استفسار المنتج وتقييم الرضا =====
PRODUCT_FOLLOWUP_DELAY_SECONDS = max(
    int(os.environ.get("PRODUCT_FOLLOWUP_DELAY_SECONDS", "43200")), 60
)
PRODUCT_FOLLOWUP_POLL_SECONDS = max(
    int(os.environ.get("PRODUCT_FOLLOWUP_POLL_SECONDS", "30")), 10
)
FOLLOWUP_WORKER_ENABLED = os.environ.get("FOLLOWUP_WORKER_ENABLED", "true").strip().lower() not in {
    "0", "false", "no", "off"
}
PRODUCT_NEXT_DAY_DELAY_SECONDS = max(
    int(os.environ.get("PRODUCT_NEXT_DAY_DELAY_SECONDS", "43200")), 60
)
PRODUCT_FOLLOWUP_SATISFIED_ID = "product_followup_satisfied"
PRODUCT_FOLLOWUP_UNSATISFIED_ID = "product_followup_unsatisfied"
PRODUCT_FOLLOWUP_CONTINUE_ID = "product_followup_continue"
PRODUCT_FOLLOWUP_STOP_ID = "product_followup_stop"
PRODUCT_RECOMMENDATION_KIND = "next_day_recommendation"
TITIZ_CHANNEL_URL = os.environ.get(
    "TITIZ_CHANNEL_URL", "https://whatsapp.com/channel/0029VaqFTglLikgDDe0D5E2D"
).strip()
PRODUCT_FOLLOWUP_SATISFIED_MESSAGE = (
    "يسعدنا رضاكِ يا غالية 😊 إذا احتجتِ أي منتج أو مساعدة، اكتبي لي في أي وقت."
)
PRODUCT_FOLLOWUP_UNSATISFIED_MESSAGE = (
    "تمام يا غالية، لن أرسل لكِ تذكيراً آخر. أنا هنا وقت ما تحتاجين أي مساعدة 😊"
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

def _compact_followup_context(value, limit=120):
    """حفظ ملخص قصير وآمن من موضوع العميل داخل التذكير."""
    return " ".join(str(value or "").split())[:limit]


def schedule_product_followup(phone_number, product_name="", inquiry_text=""):
    """جدولة تذكير واحد بعد 24 ساعة عن منتج أو استفسار العميل."""
    if phone_number and phone_number != OWNER_NUMBER:
        last_message_at = time.time()
        session_data = user_sessions.get(phone_number)
        if isinstance(session_data, dict):
            topic = _compact_followup_context(product_name or inquiry_text)
            if topic:
                session_data["last_conversation_topic"] = topic
                session_data["last_conversation_at"] = datetime.now(YEMEN_TIMEZONE).isoformat(timespec="seconds")
                user_sessions[phone_number] = session_data
        schedule_customer_followup(
            phone_number,
            _compact_followup_context(product_name),
            PRODUCT_FOLLOWUP_DELAY_SECONDS,
            context_text=_compact_followup_context(inquiry_text),
            last_message_at=last_message_at,
        )


def schedule_inquiry_followup(phone_number, inquiry_text):
    """جدولة متابعة لاستفسار عام عندما لا يكون اسم منتج محدداً."""
    context = _compact_followup_context(inquiry_text)
    if len(context) >= 3:
        schedule_product_followup(phone_number, inquiry_text=context)


def _followup_subject(product_name="", context_text=""):
    if product_name:
        return f"عن *{_compact_followup_context(product_name)}*"
    if context_text:
        return f"عن استفسارك: «{_compact_followup_context(context_text)}»"
    return "عن آخر استفسار لكِ"


def send_product_followup(phone_number, product_name="", context_text=""):
    """إرسال رسالة رضا واحدة مرتبطة بآخر منتج أو استفسار للعميل."""
    topic = _compact_followup_context(product_name or context_text) or "المنتجات المنزلية"
    message = (
        "مرحباً السادة! هل أنت راضٍ عن الردود من مساعدك الحصري، المتوفر على مدار الساعة طوال أيام الأسبوع فقط؟ 😊\n"
        "سأبقيك على اطلاع بأحدث العروض، وتوصيات المنتجات الرائجة، ومعلومات الطلبات في الوقت الفعلي.\n"
        "إذا كان لديك أي طلبات أخرى، فقط ناديني! أنا هنا من أجلك. 🛍️✨\n"
        f"بعد محادثتنا وجدنا مجموعة خاصة من {topic} لتجدها لك:\n"
        f"{TITIZ_CHANNEL_URL}"
    )
    return send_buttons(phone_number, message, [
        {"id": PRODUCT_FOLLOWUP_SATISFIED_ID, "title": "👍 راضي"},
        {"id": PRODUCT_FOLLOWUP_UNSATISFIED_ID, "title": "👎 غير راضي"},
    ])

def send_next_day_recommendation(phone_number, product_name=""):
    """إرسال توصية اليوم التالي باسم المنتج الذي بحث عنه العميل."""
    send_message(
        phone_number,
        PRODUCT_NEXT_DAY_MESSAGE_TEMPLATE.format(product_name=product_name or "المنتجات المنزلية"),
    )


def notify_owner_unfollowed_conversation(followup):
    """تنبيه واحد للإدارة عند مرور 24 ساعة بلا متابعة من العميل."""
    phone_number = str(followup.get("phone_number") or "")
    customer = get_customer(phone_number) or {}
    customer_name = str(customer.get("name") or "").strip() or "غير مسجل"
    topic = _compact_followup_context(
        followup.get("product_name") or followup.get("context_text") or "استفسار العميل"
    )
    last_message_at = followup.get("last_message_at")
    try:
        last_message_time = datetime.fromtimestamp(float(last_message_at), YEMEN_TIMEZONE).strftime("%d-%m-%Y، %H:%M")
    except (TypeError, ValueError, OSError):
        last_message_time = "غير متاح"
    notification = (
        "🔔 *محادثة تحتاج متابعة*\n"
        "━━━━━━━━━━━━\n"
        f"👤 العميل: {customer_name}\n"
        f"📞 الرقم: {phone_number}\n"
        f"📝 آخر الموضوع: {topic}\n"
        f"🕒 آخر رسالة: {last_message_time}\n"
        "⏳ لم تصل متابعة من العميل خلال 24 ساعة.\n"
        "━━━━━━━━━━━━"
    )
    return send_message(OWNER_NUMBER, notification)


def process_due_customer_followups_once():
    """معالجة التذكيرات المستحقة مرة واحدة، ليسهل اختبارها دون عامل دائم."""
    for followup in get_due_customer_followups():
        if not mark_customer_followup_sent(
            followup["phone_number"], followup["due_at"]
        ):
            continue
        # لا تُعامل توصية اليوم التالي كمحادثة متوقفة عن المتابعة.
        if followup.get("followup_kind") == PRODUCT_RECOMMENDATION_KIND:
            continue
        notify_owner_unfollowed_conversation(followup)
        if not send_product_followup(
            followup["phone_number"],
            followup.get("product_name", ""),
            followup.get("context_text", ""),
        ):
            print(f"تعذر إرسال تذكير العميل {followup['phone_number']}")

def product_followup_worker():
    """عامل خلفي يرسل التذكيرات المستحقة مرة واحدة فقط."""
    while True:
        try:
            process_due_customer_followups_once()
        except Exception as exc:
            print(f"خطأ في عامل تذكير العملاء: {exc}")
        time.sleep(PRODUCT_FOLLOWUP_POLL_SECONDS)

def start_product_followup_worker():
    """تشغيل عامل التذكير مرة واحدة لكل عملية تشغيل."""
    global followup_worker_started
    if not FOLLOWUP_WORKER_ENABLED:
        return
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
matching_send_guard = {}
MATCHING_SEND_WINDOW = 20
variant_button_context = {}
VARIANT_CONTEXT_WINDOW = 900

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


def is_low_information_query(normalized_text):
    """تمييز الحروف والمدخلات القصيرة التي لا تصلح للبحث عن منتج."""
    compact = re.sub(r"\s+", "", normalized_text or "")
    if len(compact) < 3:
        return True
    return len(set(compact)) == 1


MESSAGE_INTENT_PATTERNS = (
    ("greeting", ("هلو", "هلا", "مرحبا", "السلام عليكم", "الو", "هاي", "hello")),
    ("orders", ("طلباتي", "طلبي", "وين طلبي", "حاله طلبي", "تتبع الطلب", "الاوردر")),
    ("payment", ("تحويل", "دفعت", "الدفع", "اشعار التحويل", "حساب التحويل")),
    ("cart", ("السله", "سله", "اضف للسله", "حط بالسله", "اكمل الطلب")),
    ("offers", ("العروض", "عرض", "خصومات", "كوبون", "قناه التخفيضات")),
    ("discount", ("خصم", "نقصوا", "خفّض", "خفض", "سعر خاص", "راعونا")),
    ("price_inquiry", ("بكم", "كم السعر", "السعر كم", "كم حق", "اخر سعر")),
    ("cancel_order", ("الغاء الطلب", "الغي الطلب", "اشطب الطلب", "ما عاد اشتي")),
    ("address", ("العنوان", "موقع التوصيل", "غير العنوان", "نقطه التوصيل")),
    ("complaint", ("شكوي", "الطلب ناقص", "وصلني غلط", "ما وصل", "متاخر")),
    ("product_search", ("عندكم", "متوفر", "اشتي", "اريد", "ابغى", "وين المنتج")),
)


def classify_message_intent(text, message_type="text"):
    """تصنيف سريع قابل للتدقيق قبل الاستعانة بالنموذج الذكي."""
    if message_type == "image":
        return "product_image", 0.98
    if message_type == "audio":
        return "voice_message", 0.98
    normalized = normalize_text(text)
    if not normalized:
        return "empty", 0.99
    for intent, patterns in MESSAGE_INTENT_PATTERNS:
        if any(normalize_text(pattern) in normalized for pattern in patterns):
            return intent, 0.86
    return "unknown", 0.25


SEARCH_SPELLING_CORRECTIONS = {
    "قذور": "قدور", "كدور": "قدور", "قضور": "قدور",
    "مقرشه": "مقشره", "مقرشه بطاط": "مقشره بطاط",
    "ملاعك": "ملاعق", "ملاق": "ملاعق",
}

SEARCH_STOPWORDS = {
    "هل", "عندكم", "لديكم", "معاكم", "متوفر", "متوفره", "متوفرين", "يوجد", "توجد",
    "وين", "فين", "اين", "ايش", "وش", "ماذا", "اريد", "اشتي", "ابغى", "ابغا",
    "ممكن", "لو", "سمحتي", "سمحت", "من", "عند", "لنا", "لي", "هذا", "هاذا", "هذه",
    "هاذي", "المنتج", "منتج", "شيء", "شي", "حق", "حقكم", "مع", "عن", "في", "منكم",
}


def correct_search_spelling(normalized_text):
    """تصحيح أخطاء شائعة في سؤال المنتج دون تعديل الاسم المحفوظ في الكتالوج."""
    return " ".join(
        SEARCH_SPELLING_CORRECTIONS.get(word, word)
        for word in (normalized_text or "").split()
    )


def _searchable_product_text(product):
    return normalize_text(" ".join([
        str(product.get("name") or ""),
        str(product.get("keywords") or ""),
        str(product.get("description") or ""),
    ]))


def _fuzzy_token_match(query_token, product_tokens):
    if len(query_token) < 4:
        return False
    return any(
        len(product_token) >= 4
        and (
            query_token in product_token
            or product_token in query_token
            or difflib.SequenceMatcher(None, query_token, product_token).ratio() >= 0.76
        )
        for product_token in product_tokens
    )


JUICER_QUERY_ALIASES = {
    normalize_text(alias)
    for alias in [
        "عصاره", "عصارات", "العصاره", "العصارات", "عصارات الدار", "عصارة الدار",
        "عصارات اصليه", "عصارة اصلية", "عصارات بلاستيك", "عصارة بلاستيك",
        "عصارات ستيل", "عصارة ستيل", "عصارات استيل", "عصارة استيل",
        "عصارات مربعة", "عصارة مربعة", "عصارات مدورة", "عصارة مدورة",
        "عصارات خضار", "عصارة خضار", "عصارات خضروات", "عصارة خضروات",
        "عصارات مكسرات", "عصارة مكسرات", "عصارات فلفل", "عصارة فلفل",
        "عصارات قلات", "عصارة قلات", "عصارات يدوية", "عصارة يدوية",
        "عصارات مطبخ", "عصارة مطبخ", "عصارة المائدة",
    ]
}


def product_search_terms(msg_normalized):
    """استخراج كلمات المنتج من السؤال مع تصحيح الأخطاء وإزالة كلمات السؤال العامة."""
    corrected = correct_search_spelling(msg_normalized)
    terms = [term for term in (msg_normalized, corrected) if term]
    terms.extend(
        word for word in corrected.split()
        if len(word) >= 3 and word not in SEARCH_STOPWORDS
    )
    if corrected and any(alias in corrected for alias in JUICER_QUERY_ALIASES):
        terms.extend(["عصاره", "عصارات", "عصاره الدار", "عصارات الدار"])
    return list(dict.fromkeys(term for term in terms if term))


def match_products_from_text(query, products):
    """مطابقة اسم أو كابشن أو وصف المنتج قبل استدعاء تحليل الصورة المكلف."""
    normalized_query = normalize_text(query)
    if not normalized_query or is_low_information_query(normalized_query):
        return []
    corrected_query = correct_search_spelling(normalized_query)
    precise_phrase = " ".join(
        token for token in corrected_query.split()
        if len(token) >= 2 and token not in SEARCH_STOPWORDS
    )
    if len(precise_phrase) >= 5:
        exact_phrase_matches = [
            product for product in products or []
            if precise_phrase in _searchable_product_text(product)
        ]
        if exact_phrase_matches:
            return exact_phrase_matches
    search_terms = product_search_terms(normalized_query)
    query_tokens = {
        token for token in corrected_query.split()
        if len(token) >= 3 and token not in SEARCH_STOPWORDS
    }
    matches = []
    for product in products or []:
        searchable_text = _searchable_product_text(product)
        if any(term in searchable_text for term in search_terms if len(term) >= 3):
            matches.append(product)
            continue
        product_tokens = set(searchable_text.split())
        fuzzy_hits = sum(_fuzzy_token_match(token, product_tokens) for token in query_tokens)
        if fuzzy_hits >= 1 and (len(query_tokens) == 1 or fuzzy_hits >= 2):
            matches.append(product)
    return matches


PRODUCT_PURCHASE_KEYWORDS = [
    "اشتي هذا", "اشتي هاذا", "اشتي هذه", "اشتي هاذي", "أشتي هذا", "أشتي هاذا",
    "اريد هذا", "اريد هاذا", "اريد هذه", "اريد هاذي", "أريد هذا", "أريد هاذا",
    "ابغى هذا", "ابغا هذا", "ابغى هاذا", "ابغا هاذا", "هذا اريده", "هاذا اريده",
    "هذا لي", "هاذا لي", "احجز هذا", "احجزه", "احجزيه", "اطلبه", "اطلبيه",
    "خليه لي", "خليها لي", "اضفه للسله", "اضيفه للسله", "أضفه للسلة",
    "حطه بالسله", "حطيه بالسله", "ضيفه للسله", "اشتريه", "باخذه", "باخذ هذا",
    "هذا المنتج اريده", "هذا المنتج اشتيه", "اريد المنتج هذا", "اشتي المنتج هذا",
]
_NORMALIZED_PRODUCT_PURCHASE_KEYWORDS = {normalize_text(k) for k in PRODUCT_PURCHASE_KEYWORDS}


def is_product_purchase_request(msg_normalized):
    if not msg_normalized:
        return False
    return msg_normalized in _NORMALIZED_PRODUCT_PURCHASE_KEYWORDS or any(
        keyword in msg_normalized for keyword in _NORMALIZED_PRODUCT_PURCHASE_KEYWORDS if len(keyword) >= 5
    )


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

    # 3. مطابقة عكسية - الرسالة موجودة في كلمة مفتاحية.
    # لا نطابق كلمة قصيرة مثل «طيب» داخل عبارة طويلة مثل «عطونا سعر طيب»؛
    # فهذا يحوّل الحديث الاجتماعي إلى رد خصم غير مرتبط بسياق العميل.
    for key, data in UNIFIED_RESPONSES.items():
        if len(msg_normalized) >= 5 and msg_normalized in key:
            return data

    return None

# ===== تسجيل الردود المبرمجة =====

RESP_DISCOUNT = (
    "أبشري يا غالية 😊\n\n"
    "أسعارنا مخفّضة من البداية ونحرص دائماً نعطيك أفضل سعر ممكن 💛\n"
    "إذا كانت الكمية أكثر من قطعة، أرسلي اسم المنتج والعدد المطلوب، "
    "وبنراجع لكِ أفضل سعر مع الإدارة بإذن الله 🤝\n\n"
    "اكتبي اسم المنتج أو أرسلي صورة المنتج، وأنا أطلع لكِ السعر الحالي مباشرة 🛍️"
)

DELEGATE_WHATSAPP_NUMBER = "967712282204"
DELEGATE_WHATSAPP_URL = (
    f"https://wa.me/{DELEGATE_WHATSAPP_NUMBER}"
    f"?text={quote('مرحباً، أريد الاستفسار عن السعر والمنتج')}"
)
PRICE_INQUIRY_RESPONSE = (
    "أبشري يا غالية 😊\n\n"
    "أسعارنا مخفّضة من البداية ونحرص دائماً نعطيك أفضل سعر ممكن 💛\n"
    "إذا كانت الكمية أكثر من قطعة، أرسلي اسم المنتج والعدد المطلوب، وبنراجع لكِ أفضل سعر مع الإدارة بإذن الله 🤝"
)
OFFERS_CHANNEL_URL = "https://whatsapp.com/channel/0029VaqFTglLikgDDe0D5E2D"
OFFERS_RESPONSE = (
    "يمكنك العثور على أحدث العروض والخصومات على قناة تخفيضات *Titiz* للأدوات المنزلية "
    "(تجزئة) في واتساب 📢\n\n"
    f"🔗 {OFFERS_CHANNEL_URL}\n\n"
    "من خلال عدة طرق:\n\n"
    "1. *عروض Big Save:* ابحثي عن المنتجات الحصرية، حيث يمكنك الحصول على خصومات "
    "في أقسام مخصصة على الصفحة الرئيسية.\n"
    "2. *الكوبونات:* قد تتوفر كوبونات من المنصة أو من المتاجر مباشرة، ويمكنك التحقق منها عبر قناتنا.\n"
    "3. *عروض المشترين الجدد:* إذا كانت هذه أول عملية شراء لكِ، فقد تتوفر عروض أو أكواد ترويجية حصرية.\n\n"
    "تابعي القناة ليصلكِ كل جديد من المنتجات والعروض أولاً بأول 🛍️✨"
)
OFFERS_KEYWORDS = [
    "وين العروض", "وين تنزل العروض", "وين تنزلو العروض", "وين تنزلوا العروض",
    "اين العروض", "أين العروض", "فين العروض", "فين تنزل العروض", "فين تنزلو العروض",
    "العروض وين", "العروض فين", "عروضكم وين", "عروضكم فين",
    "عندكم عروض", "عندكم عرض", "في عروض", "فيه عروض", "في عرض", "فيه عرض",
    "وين العرض", "وين تنزلوا العروض", "وين تنزلون العروض", "متى العروض",
    "عروض اليوم", "عروض جديدة", "العروض الجديدة", "العروض الحالية", "العرض الحالي",
    "عروض خاصة", "عروض حصرية", "عروض القناة", "قناة العروض", "قناة التخفيضات",
    "التخفيضات", "تخفيضات", "تنزيلات", "تنزيلاتكم", "تنزلوا العروض",
    "تنشروا العروض", "تنشرون العروض", "من وين اشوف العروض", "كيف اشوف العروض",
    "كيف اعرف العروض", "ارسلوا العروض", "رابط العروض", "رابط قناة العروض",
    "رابط القناة", "ايش العروض", "وش العروض", "ما هي العروض", "العروض ايش",
    "عروض وخصومات", "وين الخصومات", "خصوماتكم وين", "في كوبونات", "كوبونات",
    "كوبون خصم", "كود خصم", "عرض المشترين الجدد", "عرض المشتري الجديد",
    "Big Save", "بيج سيف",
]
_NORMALIZED_OFFERS_KEYWORDS = {normalize_text(k) for k in OFFERS_KEYWORDS}


def is_offers_inquiry(msg_normalized):
    if not msg_normalized:
        return False
    return msg_normalized in _NORMALIZED_OFFERS_KEYWORDS or any(
        len(keyword) >= 5 and keyword in msg_normalized
        for keyword in _NORMALIZED_OFFERS_KEYWORDS
    )


def send_offers_response(to):
    """إرسال رابط قناة العروض مع زر مباشر للمندوبة."""
    if not whatsapp.send_url_button(
        to,
        OFFERS_RESPONSE,
        "📞 التواصل مع المندوبة",
        DELEGATE_WHATSAPP_URL,
    ):
        send_message(
            to,
            OFFERS_RESPONSE
            + f"\n\n📞 للتواصل مع المندوبة مباشرة:\n{DELEGATE_WHATSAPP_URL}",
        )
PRICE_INQUIRY_KEYWORDS = [
    "بكم", "بكم هذا", "بكم هذي", "بكم المنتج", "كم السعر", "السعر كم",
    "كم سعره", "كم سعرها", "كم سعر المنتج", "كم حقه", "كم حقها",
    "كم حق المنتج", "بكم تبيعوا", "كم تبيعوا", "كم القيمة", "قيمة المنتج",
]
_NORMALIZED_PRICE_INQUIRY_KEYWORDS = {normalize_text(k) for k in PRICE_INQUIRY_KEYWORDS}


def is_price_inquiry(msg_normalized):
    if not msg_normalized:
        return False
    return msg_normalized in _NORMALIZED_PRICE_INQUIRY_KEYWORDS or any(
        len(keyword) >= 4 and keyword in msg_normalized
        for keyword in _NORMALIZED_PRICE_INQUIRY_KEYWORDS
    )


def send_price_inquiry_response(to):
    """إرسال رد سؤال السعر مع زر CTA يفتح محادثة المندوبة."""
    if not whatsapp.send_url_button(
        to,
        PRICE_INQUIRY_RESPONSE,
        "📞 التواصل مع المندوبة",
        DELEGATE_WHATSAPP_URL,
    ):
        send_message(
            to,
            PRICE_INQUIRY_RESPONSE
            + f"\n\n📞 للتواصل مع المندوبة مباشرة:\n{DELEGATE_WHATSAPP_URL}",
        )

add_response(
    [
        "نقصوا لنا", "نقصوا السعر", "نقص السعر", "نقصي السعر", "نقص لنا",
        "نقص من السعر", "خفّض السعر", "خفض السعر", "خفضوا السعر", "خلي السعر اقل",
        "خلي السعر أقل", "ممكن تخفيض", "ممكن تنقص", "ينفع تخفيض", "في خصم",
        "فيه خصم", "هل فيه خصم", "هل يوجد خصم", "اعمل خصم", "اعملوا خصم",
        "سوي لنا خصم", "سووا لنا خصم", "سعر نهائي", "آخر سعر", "اخر سعر",
        "ارخص لنا", "ارخص", "السعر غالي", "غالي", "مافي تخفيض", "مافي خصم",
        "احنا زبائن", "احنا زباين", "احنا زبان", "نحن زبائن", "نحن زباين",
        "نحن زبان", "انا زبون", "انا زبونه", "انا زبونة", "من زبائنكم",
        "من زباينكم", "من زبانكم", "زبائن عندكم", "زباين عندكم", "زبان عندكم",
        "احنا زبائن عندكم", "احنا زباين عندكم", "احنا زبان عندكم",
        "نحن زبائن عندكم", "نحن زباين عندكم", "نحن زبان عندكم",
        "زبائن دائمين", "زباين دائمين", "زبائن دايمين", "زباين دايمين",
        "عميل دائم", "عميله دائمه", "عميلة دائمة", "عميل قديم", "عميله قديمه",
        "اشترينا منكم قبل", "اشترينا عندكم قبل", "نشتري منكم دائما", "نشتري منكم دايم",
        "احنا عملاء دائمين", "نحن عملاء دائمين", "راعونا كزبائن", "راعونا يا زبائن",
        "اكسبونا زبائن", "اكسبونا زباين", "اكسبونا زبان", "اكسبونا كزبائن",
        "اكسبونا كزباين", "اكسبوا نا زبائن", "اكسبوا نا زباين", "اكسبو نا زبان",
        "اكسبو لنا زبائن", "اكسبوا لنا زبائن", "اكسبونا عميل", "اكسبونا عملاء",
        "خلونا زبائن", "خلونا من زبائنكم", "نكون من زبائنكم", "نصير زبائنكم",
        "اعملوا لنا سعر خاص", "اعمل لنا سعر خاص", "اعطونا سعر خاص", "عطونا سعر خاص",
        "سعر الزبون", "سعر خاص للزبون", "سعر خاص للزبائن", "سعر للزبائن",
        "راعونا بالسعر", "راعينا بالسعر", "راعي لنا السعر", "ساعدونا بالسعر",
        "ساعدونا شوي", "خففوا علينا", "خفف علينا", "نقصوا علينا", "نزلوا لنا",
        "نزل لنا السعر", "نزل السعر شوي", "نقصها لنا", "نقصها شوي", "خلوها ارخص",
        "لو اخذت كمية", "اذا اخذت كمية", "اذا اخذنا كمية", "معي كمية",
        "باخذ كمية", "ناخذ كمية", "نشتري بالجملة", "للجملة", "سعر الجملة",
        "خصم كمية", "خصم للكمية", "خصم للزبائن", "خصم للعميل", "طلب كمية",
        "اشتي خصم", "اشتي تخفيض", "ابغى خصم", "ابغا خصم", "ابغى تخفيض",
        "اعمل لنا تخفيض", "اعملوا لنا تخفيض", "سوي لنا تخفيض", "سووا تخفيض",
        "التخفيض كم", "في تنزيل", "نزلو السعر", "ممكن تنزلوا السعر",
        "ممكن تنقصوا السعر", "ممكن ترخصوا", "سوي لنا رخص", "عطونا سعر طيب",
        "اعطونا سعر طيب", "بكم اخر شي", "كم اخر سعر", "كم اخرها", "ايش اخر سعر",
        "وش اخر سعر", "هذا اخر سعر", "مافي سعر اقل", "مافي ارخص", "نريد ارخص",
    ],
    RESP_DISCOUNT,
)

add_response(PRICE_INQUIRY_KEYWORDS, PRICE_INQUIRY_RESPONSE)
add_response(OFFERS_KEYWORDS, OFFERS_RESPONSE)

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
    ["هاي", "هااي", "هلو", "هلوو", "هلو والله", "الو", "الوو", "hi", "hello", "hey"],
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
RESP_PRODUCTS_ASK = "🏠 أهلاً فيكِ يا غالية! ✨\n\nلدينا جميع الأدوات المنزلية ومستلزمات المطابخ 🍳\n\nايش بدكِ أنتِ من منتج؟ 😊"
add_response(
    [
        "ايش عندكم", "ايش معاكم", "وش عندكم", "وش معاكم",
        "ايش تبيعون", "ايش تبيعو", "ايش تبيعوا", "وش تبيعون", "وش تبيعو", "وش تبيعوا",
        "ايش منتجاتكم", "وش منتجاتكم", "ايش بضاعتكم", "وش بضاعتكم",
        "ايش البضاعة", "ايش البضاعه", "وش البضاعة", "وش البضاعه",
        "ايش عندكم من منتجات", "ايش معاكم من منتجات", "وش عندكم من منتجات", "وش معاكم من منتجات",
        "ايش عندكم منتجات", "ايش معاكم منتجات", "وش عندكم منتجات", "وش معاكم منتجات",
        "ايش عندكم من بضاعة", "ايش معاكم من بضاعة", "وش عندكم من بضاعة",
        "منتجات", "المنتجات", "بضاعة", "البضاعة", "البضاعه",
        "ايش في", "وش في", "ايش موجود", "وش موجود", "ايش المتوفر", "وش المتوفر",
        "عندكم ايش", "معاكم ايش", "عندكم منتجات ايش", "معاكم منتجات ايش",
    ],
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
GUIDED_HELP_MESSAGE = (
    "أنا معك يا غالية 😊\n"
    "أقدر أساعدك في البحث عن أي أداة منزلية، متابعة طلباتك، أو معرفة العروض.\n"
    "اختاري الخدمة المناسبة أو اكتبي طلبك بطريقتك، وسأتابع معك خطوة بخطوة."
)
SOCIAL_OR_CONFUSED_PHRASES = {
    "هههه", "ههههه", "هههههه", "هاها", "هاهاها", "احبك", "احبج", "احسك",
    "ايش", "ايش؟", "مافهمت", "ما فهمت", "وش", "وش؟", "كيف", "كيف?",
    "انت روبوت", "انتي روبوت", "تفهمني", "تفهميني", "تجربه", "اختبار",
    "ما اعرف", "مدري", "ما ادري", "ساعدني", "ساعديني", "ابغى مساعده",
}
POSITIVE_SOCIAL_PHRASES = {
    "حلو", "حلوه", "حلوة", "جميل", "جميله", "جميلة", "ممتاز", "ممتازه",
    "ممتازة", "رائع", "رائعه", "رائعة", "تمام", "طيب", "اوكي", "اوكيه",
    "حلو منتجكم", "منتجكم حلو", "منتجاتكم حلوه", "متجركم حلو", "متجركم جميل",
    "عجبني", "عجبني المنتج", "عجبني متجركم", "شكرا", "شكراً", "يسلمو",
}
FRUSTRATION_OR_CONFUSION_PHRASES = {
    "ما تفهم", "ما تفهم انت", "ما تفهمي", "ما فهمت علي", "مافهمت علي",
    "مو فاهم", "مش فاهم", "ما تعرف", "ما تعرفي", "الرد غلط", "غلط",
}
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

def sync_products_to_github(remove_names=None):
    """دمج المنتجات المحلية مع GitHub، مع حذف مفاتيح قديمة عند التعديل أو الحذف."""
    try:
        if not GITHUB_TOKEN:
            print("[GitHub] GITHUB_TOKEN غير موجود؛ تم إلغاء الحفظ الآمن.")
            return False

        remote_data, sha = github_load("products.json")
        products_dict = remote_data if isinstance(remote_data, dict) else {}
        if remove_names:
            remove_normalized = {normalize_text(name) for name in remove_names if name}
            for key in list(products_dict):
                remote_name = products_dict.get(key, {}).get("name", key)
                if normalize_text(str(key)) in remove_normalized or normalize_text(str(remote_name)) in remove_normalized:
                    del products_dict[key]
        products = get_all_products()
        for p in products:
            raw_variants = p.get("variants", "")
            if isinstance(raw_variants, str) and raw_variants.startswith("["):
                try:
                    raw_variants = json.loads(raw_variants)
                except json.JSONDecodeError:
                    pass
            products_dict[p["name"]] = {
                "name": p["name"],
                "price": str(int(p["price"])),
                "description": p.get("description", ""),
                "keywords": p.get("keywords", ""),
                "image_id": p.get("image_id", ""),
                "image_urls": p.get("image_urls", ""),
                "variants": raw_variants
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
    """تحميل المنتجات عند بدء التشغيل من GitHub، مع fallback للنسخة المرفقة."""
    try:
        data, sha = github_load("products.json")
        source = "GitHub"
        if not isinstance(data, dict) or not data:
            local_path = os.path.join(os.path.dirname(__file__), "products.json")
            try:
                with open(local_path, "r", encoding="utf-8") as catalog_file:
                    local_data = json.load(catalog_file)
                if isinstance(local_data, dict) and local_data:
                    data = local_data
                    source = "النسخة المحلية"
            except Exception as local_error:
                print(f"[بدء التشغيل] تعذر قراءة النسخة المحلية من products.json: {local_error}")
        if data:
            count = 0
            existing = get_all_products()
            existing_names = {normalize_text(p["name"]) for p in existing}
            for name, info in data.items():
                if not isinstance(info, dict):
                    continue
                price = 0
                try:
                    price = float(info.get("price", "0"))
                except (TypeError, ValueError):
                    pass
                desc = info.get("description", "")
                image_id = info.get("image_id", "")
                image_urls = info.get("image_urls", "")
                if isinstance(image_urls, list):
                    image_urls = json.dumps(image_urls, ensure_ascii=False)
                variants = info.get("variants", "")
                if isinstance(variants, list):
                    variants = json.dumps(variants, ensure_ascii=False)
                keywords = info.get("keywords", "")
                if isinstance(keywords, list):
                    keywords = ",".join(keywords)
                normalized_name = normalize_text(name)
                if normalized_name not in existing_names:
                    product_id = add_product(name, price, desc, image_id, 100, keywords, image_urls, variants)
                    if product_id:
                        existing_names.add(normalized_name)
                        count += 1
                else:
                    update_product_metadata(name, price, desc, image_id, keywords, image_urls, variants)
            print(f"[بدء التشغيل] تم تحميل {count} منتج من {source} (إجمالي: {len(data)})")
        else:
            print("[بدء التشغيل] لا توجد منتجات في GitHub أو النسخة المحلية")
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

def _record_outbound_event(to, message_type, body="", media_id=""):
    """حفظ الرد الصادر وربطه بآخر رسالة واردة للعميل دون تعطيل الإرسال."""
    try:
        return record_message_event(
            direction="outbound",
            phone_number=to,
            message_type=message_type,
            body=body or "",
            response_text=body or "",
            media_id=media_id,
        )
    except Exception as exc:
        print(f"[سجل الرسائل] تعذر حفظ الرد الصادر: {exc}")
        return None


def _voice_text(text):
    """تنظيف نص الرد واحتواؤه في طول مناسب لمقطع صوتي قصير."""
    cleaned = re.sub(r"[*_`~]", "", str(text or ""))
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > VOICE_REPLY_MAX_CHARS:
        cleaned = cleaned[:VOICE_REPLY_MAX_CHARS].rsplit(" ", 1)[0].strip() + "..."
    return cleaned


async def _generate_female_voice_audio(spoken_text):
    """توليد MP3 عربي بصوت أنثوي عبر خدمة Edge TTS."""
    output = io.BytesIO()
    communicate = edge_tts.Communicate(spoken_text, VOICE_REPLY_VOICE, rate="+0%", pitch="+0Hz")
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            output.write(chunk.get("data", b""))
    return output.getvalue()


def _send_voice_reply_if_needed(to, text):
    """يرسل أول رد للرسالة الصوتية كمقطع صوتي، ويعيد False للنص الاحتياطي عند التعذر."""
    if not VOICE_REPLY_ENABLED or not voice_reply_mode.get() or voice_reply_sent.get():
        return False
    spoken_text = _voice_text(text)
    if not spoken_text:
        return False
    try:
        audio_bytes = asyncio.run(_generate_female_voice_audio(spoken_text))
        if len(audio_bytes) < 512:
            raise ValueError("ملف الرد الصوتي قصير جداً")
        if whatsapp.send_audio(to, audio_bytes, "audio/mpeg", "titiz-reply.mp3"):
            _record_outbound_event(to, "audio", spoken_text)
            voice_reply_sent.set(True)
            return True
    except Exception as exc:
        print(f"[الصوت] تعذر إنشاء أو إرسال الرد الصوتي: {exc}")
    return False


def send_message(to, text):
    if _send_voice_reply_if_needed(to, text):
        return True
    result = whatsapp.send_message(to, text)
    if result:
        _record_outbound_event(to, "text", text)
    return result

def _audio_extension(mime_type):
    """اختيار امتداد مؤقت مناسب لصوت واتساب."""
    mime = (mime_type or "").lower()
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "mp4" in mime or "m4a" in mime:
        return ".m4a"
    if "aac" in mime:
        return ".aac"
    if "amr" in mime:
        return ".amr"
    return ".ogg"

def _request_with_429_retry(request_func, request_name, *args, retries=None, retry_base=None, **kwargs):
    """تنفيذ طلب خارجي مع انتظار تدريجي عند تجاوز الحد 429."""
    max_retries = max(int(retries if retries is not None else VOICE_MAX_RETRIES), 1)
    base_seconds = max(float(retry_base if retry_base is not None else VOICE_RETRY_BASE_SECONDS), 0.2)
    last_response = None
    for attempt in range(max_retries):
        response = request_func(*args, **kwargs)
        last_response = response
        if response.status_code != 429:
            return response

        retry_after_header = getattr(response, "headers", {}).get("Retry-After")
        try:
            retry_after = float(retry_after_header) if retry_after_header else 0
        except (TypeError, ValueError):
            retry_after = 0
        delay = max(retry_after, base_seconds * (2 ** attempt))
        print(
            f"[الخدمة] {request_name}: 429 Too Many Requests "
            f"(محاولة {attempt + 1}/{max_retries})، انتظار {delay:.1f} ثانية"
        )
        if attempt < max_retries - 1:
            time.sleep(delay)

    last_response.raise_for_status()
    return last_response


def _llm_token_limit(limit):
    """اختيار اسم حد الإخراج المتوافق مع عائلة النموذج المضبوطة."""
    if SMART_AI_MODEL.lower().startswith("gpt-5"):
        return {"max_completion_tokens": int(limit)}
    return {"max_tokens": int(limit)}


def _semantic_response_format():
    """إجبار النموذج على بنية نية آمنة وقابلة للتوجيه بدلاً من نص حر."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "titiz_customer_intent",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "enum": sorted(SEMANTIC_INTENTS)},
                    "confidence": {"type": "number"},
                    "search_query": {"type": "string"},
                    "reply": {"type": "string"},
                },
                "required": ["intent", "confidence", "search_query", "reply"],
                "additionalProperties": False,
            },
        },
    }

def download_whatsapp_audio(audio_data):
    """تنزيل ملف صوتي من WhatsApp Cloud API باستخدام media_id أو url."""
    media_id = (audio_data or {}).get("id", "")
    media_url = (audio_data or {}).get("url", "")
    if not media_id and not media_url:
        raise ValueError("لم يصل معرف ملف الصوت من واتساب")
    if not ACCESS_TOKEN:
        raise ValueError("ACCESS_TOKEN غير مضبوط")

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    if media_id:
        media_response = _request_with_429_retry(
            requests.get,
            "جلب بيانات الصوت من واتساب",
            f"https://graph.facebook.com/v26.0/{media_id}",
            headers=headers,
            params={"phone_number_id": PHONE_NUMBER_ID},
            timeout=15,
        )
        media_response.raise_for_status()
        media_url = media_response.json().get("url", "")
    if not media_url:
        raise ValueError("لم يتم الحصول على رابط ملف الصوت")

    audio_response = _request_with_429_retry(
        requests.get,
        "تنزيل ملف الصوت من واتساب",
        media_url,
        headers=headers,
        timeout=30,
    )
    audio_response.raise_for_status()
    if len(audio_response.content) > 16 * 1024 * 1024:
        raise ValueError("ملف الصوت أكبر من الحد المدعوم")
    mime_type = audio_response.headers.get("Content-Type") or audio_data.get(
        "mime_type", "audio/ogg"
    )
    return audio_response.content, mime_type


def download_whatsapp_image(image_data):
    """تنزيل صورة العميل من WhatsApp Cloud API وتحويلها إلى بيانات قابلة للتحليل."""
    media_id = (image_data or {}).get("id", "")
    media_url = (image_data or {}).get("url", "")
    if not media_id and not media_url:
        raise ValueError("لم يصل معرف صورة المنتج من واتساب")
    if not ACCESS_TOKEN:
        raise ValueError("ACCESS_TOKEN غير مضبوط")

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    if media_id:
        media_response = _request_with_429_retry(
            requests.get,
            "جلب بيانات صورة المنتج من واتساب",
            f"https://graph.facebook.com/v26.0/{media_id}",
            headers=headers,
            params={"phone_number_id": PHONE_NUMBER_ID},
            timeout=15,
        )
        media_response.raise_for_status()
        media_url = media_response.json().get("url", "")
    if not media_url:
        raise ValueError("لم يتم الحصول على رابط صورة المنتج")

    image_response = _request_with_429_retry(
        requests.get,
        "تنزيل صورة المنتج من واتساب",
        media_url,
        headers=headers,
        timeout=30,
    )
    image_response.raise_for_status()
    if len(image_response.content) > 16 * 1024 * 1024:
        raise ValueError("صورة المنتج أكبر من الحد المدعوم")
    mime_type = image_response.headers.get("Content-Type") or image_data.get(
        "mime_type", "image/jpeg"
    )
    if not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    return image_response.content, mime_type

def transcribe_voice_message(message):
    """تحويل الرسالة الصوتية إلى نص عربي باستخدام خدمة تفريغ الصوت."""
    if not VOICE_TRANSCRIPTION_API_KEY:
        print("[الصوت] VOICE_TRANSCRIPTION_API_KEY غير مضبوط")
        return None
    audio_data = message.get("audio", {})
    media_id = audio_data.get("id", "")
    if not voice_processing_lock.acquire(blocking=False):
        raise RuntimeError("VOICE_BUSY")
    try:
        now = time.time()
        if media_id and now - voice_recent_media.get(media_id, 0) < VOICE_DEDUP_SECONDS:
            raise RuntimeError("VOICE_DUPLICATE")
        audio_bytes, mime_type = download_whatsapp_audio(audio_data)
        extension = _audio_extension(mime_type)
        headers = {"Authorization": f"Bearer {VOICE_TRANSCRIPTION_API_KEY}"}
        files = {"file": (f"voice{extension}", audio_bytes, mime_type)}
        form_data = {
            "model": VOICE_TRANSCRIPTION_MODEL,
            "language": "ar",
            "response_format": "json",
            "prompt": "هذه رسالة صوتية عربية باللهجة اليمنية عن متجر Titiz للأدوات المنزلية والطلبات والدفع والتوصيل.",
        }
        response = _request_with_429_retry(
            requests.post,
            "تحويل الصوت إلى نص",
            f"{VOICE_TRANSCRIPTION_API_BASE}/audio/transcriptions",
            headers=headers,
            files=files,
            data=form_data,
            timeout=90,
        )
        response.raise_for_status()
        text = (response.json().get("text") or "").strip()
        if media_id:
            voice_recent_media[media_id] = time.time()
        return text or None
    finally:
        voice_processing_lock.release()

def build_conversation_context(sender, limit=10):
    """بناء ذاكرة مختصرة من آخر رسائل العميل وردود البوت."""
    try:
        events = list(reversed(get_message_events(limit=limit, phone_number=sender)))
    except Exception as exc:
        print(f"[الذاكرة] تعذر قراءة سياق العميل: {exc}")
        return "لا يوجد سياق سابق متاح."
    lines = []
    for event in events:
        direction = "العميل" if event.get("direction") == "inbound" else "البوت"
        content = event.get("body") or event.get("caption") or event.get("response_text") or "[وسائط]"
        content = str(content).strip().replace("\n", " ")
        if content:
            lines.append(f"{direction}: {content[:500]}")
    return "\n".join(lines[-limit:]) or "لا يوجد سياق سابق متاح."


def _parse_json_object(text):
    """استخراج JSON من رد النموذج حتى لو وضعه داخل code fence."""
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(text).strip(), flags=re.IGNORECASE)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def interpret_customer_message(sender, user_text):
    """فهم الرسالة وسياقها عبر LLM وإرجاع نية قابلة للتنفيذ، لا رد حر فقط."""
    if not SMART_AI_API_KEY or not user_text:
        return None
    products = get_all_products()[:60]
    product_context = "\n".join(
        f"- {p.get('name', '')} | كلمات: {p.get('keywords', '')} | وصف: {p.get('description', '')[:240]}"
        for p in products
    ) or "لا توجد منتجات محملة حالياً."
    context = build_conversation_context(sender)
    system_prompt = (
        "أنت طبقة فهم الرسائل لموظفة Titiz الذكية. افهم العربية واللهجة اليمنية والأخطاء الإملائية، "
        "ولا تكتفِ بمطابقة الكلمات حرفياً. أعد JSON فقط بلا Markdown بهذه المفاتيح: "
        "intent, confidence, search_query, reply. "
        "intent يجب أن يكون واحداً من: product_search, product_purchase, price_inquiry, orders, "
        "cart, payment, offers, discount, complaint, greeting, clarification, general, social_chat, "
        "affirmation, rejection, product_choice, quantity_change, comparison, budget, agent_handoff, stop_reminder, "
        "shipping, location, warranty, catalog, out_of_scope. "
        "إذا كان الكلام عن منتج أو وصفه، صحح المعنى في search_query باستخدام اسم أو كلمات الكتالوج. "
        "عند الضحك أو المزاح أو اختبار البوت استخدم social_chat ورداً لطيفاً ثم اسأل كيف تساعد العميل. "
        "عند عدم كفاية المعلومات استخدم clarification واسأل سؤالاً واحداً قصيراً فقط. "
        "عند المدح أو الكلام القصير مثل حلو أو تمام أو طيب، استخدم affirmation أو social_chat، "
        "وأكمل من آخر منتج أو موضوع في السياق بدلاً من الانتقال إلى الخصم أو السعر. "
        "لا تكرر كلام العميل، ولا تقترح خصماً إلا إذا طلب العميل تخفيضاً أو سعراً خاصاً بوضوح. "
        "لكل رسالة عميل اختر رداً واحداً فقط، ولا تجمع ردوداً متعددة أو قوائم متعددة. "
        "عند الموافقة أو الرفض أو الأول والثاني استخدم السياق السابق ولا تنفذ شراء أو إلغاء من دون تأكيد صريح. "
        "عند طلب مندوبة استخدم agent_handoff، وعند طلب إيقاف التذكير استخدم stop_reminder. "
        "استخدمي shipping للتوصيل، location للموقع، warranty للضمان أو الاستبدال، catalog لسؤال ماذا نبيع، "
        "وout_of_scope عندما لا يتعلق السؤال بمنتجات Titiz أو خدماتها؛ عندها اطلبي توضيحاً قصيراً ولا تخمني. "
        "إذا كان المنتج أو السعر غير موجود في البيانات فلا تخترع سعراً. reply يكون فارغاً عندما يحتاج "
        "المسار بطاقة منتج أو سلة، ويكون رداً عربياً قصيراً فقط للنوايا العامة. "
        "استخدم السياق لفهم كلمات مثل هذا وهاذا وأريده والطلب السابق.\n\n"
        f"السياق السابق:\n{context}\n\n"
        f"الكتالوج المتاح:\n{product_context}"
    )
    payload = {
        "model": SMART_AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
        **_llm_token_limit(300),
        "response_format": _semantic_response_format(),
    }
    event_id = active_message_events.get(sender)
    try:
        response = _request_with_429_retry(
            requests.post,
            "فهم رسالة العميل",
            f"{SMART_AI_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {SMART_AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
            retries=1,
            retry_base=0.2,
        )
        response.raise_for_status()
        raw_result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        result = _parse_json_object(raw_result)
        if not result:
            if event_id:
                update_message_event(event_id, ai_model=SMART_AI_MODEL, ai_status="invalid_json", ai_result=raw_result)
            return None
        intent = str(result.get("intent") or "general").strip()
        if intent not in SEMANTIC_INTENTS:
            intent = "general"
        try:
            confidence = float(result.get("confidence") or 0.5)
        except (TypeError, ValueError):
            confidence = 0.5
        result["intent"] = intent
        result["confidence"] = max(0.0, min(confidence, 1.0))
        if event_id:
            update_message_event(
                event_id,
                intent=intent,
                intent_confidence=result["confidence"],
                ai_model=SMART_AI_MODEL,
                ai_status="success",
                ai_result=json.dumps(result, ensure_ascii=False),
            )
        return result
    except Exception as exc:
        if event_id:
            update_message_event(event_id, ai_model=SMART_AI_MODEL, ai_status="error", ai_result=str(exc))
        raise


def route_semantic_intent(sender, msg_body, semantic_result, products=None):
    """تحويل نية LLM إلى مسار آمن. يعيد True عندما أرسل البوت رداً."""
    if not semantic_result:
        return False
    semantic_intent = str(semantic_result.get("intent") or "general").strip()
    semantic_query = str(semantic_result.get("search_query") or msg_body or "").strip()
    semantic_reply = str(semantic_result.get("reply") or "").strip()
    products = products if products is not None else get_all_products()

    if semantic_intent in {"product_search", "product_purchase", "product_choice"}:
        semantic_matching = match_products_from_text(semantic_query, products)
        if len(semantic_matching) == 1:
            found_product = semantic_matching[0]
            user_sessions[sender] = {
                **(user_sessions.get(sender, {}) if isinstance(user_sessions.get(sender, {}), dict) else {}),
                "last_product_id": found_product.get("id"),
                "last_product": found_product,
            }
            # لا نضيف إلى السلة إلا عندما تكون نية الشراء صريحة والمنتج بلا خيارات.
            if semantic_intent == "product_purchase" and not product_variants(found_product):
                if add_to_cart(sender, int(found_product.get("id"))):
                    send_message(sender, f"✅ تم إضافة {found_product.get('name', 'المنتج')} إلى السلة.")
                    send_cart_view(sender)
                    return True
            send_product_card(sender, found_product)
            return True
        if len(semantic_matching) > 1:
            send_matching_products_carousel(sender, semantic_matching, semantic_query)
            return True

    if semantic_intent == "orders":
        send_customer_orders(sender)
        return True
    if semantic_intent == "price_inquiry":
        send_price_inquiry_response(sender)
        schedule_inquiry_followup(sender, semantic_query)
        return True
    if semantic_intent == "offers":
        send_offers_response(sender)
        schedule_inquiry_followup(sender, semantic_query)
        return True
    if semantic_intent == "catalog":
        send_product_request_menu(sender)
        return True
    if semantic_intent in {"shipping", "location", "warranty"}:
        service_keywords = {
            "shipping": "التوصيل",
            "location": "الموقع",
            "warranty": "الضمان",
        }
        service_response = find_response(normalize_text(service_keywords[semantic_intent]))
        if service_response:
            send_response(sender, service_response)
        else:
            send_guided_help(sender, semantic_reply)
        schedule_inquiry_followup(sender, semantic_query)
        return True
    if semantic_intent == "cart":
        send_cart_view(sender)
        return True
    if semantic_intent == "payment":
        send_payment_choice(sender)
        return True
    if semantic_intent == "discount":
        send_price_inquiry_response(sender)
        return True
    if semantic_intent == "complaint":
        request_customer_complaint(sender)
        return True
    if semantic_intent == "greeting":
        send_welcome(sender)
        return True
    if semantic_intent == "stop_reminder":
        cancel_customer_followup(sender)
        send_message(sender, "✅ تم إيقاف التذكير لكِ. أنا هنا وقت ما تحتاجين أي مساعدة 😊")
        return True
    if semantic_intent == "agent_handoff":
        if not whatsapp.send_url_button(
            sender,
            "أكيد يا غالية، تواصلي مباشرة مع المندوبة وستساعدكِ في طلبك 😊",
            "📞 التواصل مع المندوبة",
            DELEGATE_WHATSAPP_URL,
        ):
            send_message(sender, f"📞 تواصلي مع المندوبة مباشرة:\n{DELEGATE_WHATSAPP_URL}")
        schedule_inquiry_followup(sender, semantic_query)
        return True

    if semantic_intent in {"social_chat", "clarification", "general"}:
        send_guided_help(sender, semantic_reply)
        if semantic_intent != "social_chat":
            schedule_inquiry_followup(sender, semantic_query)
        return True
    if semantic_intent == "out_of_scope":
        send_guided_help(
            sender,
            semantic_reply or "أقدر أساعدكِ بمنتجات Titiz والطلبات والسلة والدفع والعروض 😊",
        )
        return True

    if semantic_intent in {
        "affirmation", "rejection", "quantity_change", "comparison", "budget",
        "complaint", "discount", "payment",
    }:
        if semantic_reply:
            send_message(sender, semantic_reply)
        else:
            send_message(sender, "أنا معك يا غالية 😊 هل تبحثين عن منتج، تتابعين طلباً، أم تحتاجين مساعدة بشيء آخر؟")
        if semantic_intent in {"comparison", "budget"}:
            schedule_inquiry_followup(sender, semantic_query)
        return True
    return False


def generate_smart_reply(sender, user_text):
    """إنشاء رد عربي ذكي للاستفسارات التي لا يغطيها الرد المبرمج."""
    if not SMART_AI_API_KEY or not user_text:
        return None
    products = get_all_products()[:40]
    product_context = "\n".join(
        f"- {p.get('name', '')}: {p.get('price', 0)} ريال — {p.get('description', '')}"
        for p in products
    ) or "لا توجد منتجات محملة حالياً."
    state = user_states.get(sender, "")
    conversation_context = build_conversation_context(sender)
    system_prompt = (
        "أنت موظفة Titiz الذكية لمتجر أدوات منزلية في إب، اليمن. "
        "أجيبي بالعربية وبأسلوب يمني لطيف وواضح، مع إيموجي قليلة ومناسبة. "
        "افهمي السؤال حتى لو كان باللهجة أو به أخطاء إملائية. "
        "لا تخترعي منتجاً أو سعراً أو حالة طلب غير موجودة. "
        "إذا كان السؤال عن منتج موجود في القائمة فاذكري اسمه وسعره ووصفه باختصار، "
        "وإذا أراد العميل الشراء فاطلبي منه كتابة اسم المنتج أو استخدام السلة. "
        "لا تطلبي بيانات حساسة، ولا تدّعي تنفيذ طلب أو دفع لم ينفذه النظام.\n\n"
        f"حالة المحادثة الحالية: {state or 'لا توجد حالة خاصة'}\n"
        f"سياق آخر الرسائل:\n{conversation_context}\n"
        f"المنتجات المتاحة:\n{product_context}"
    )
    payload = {
        "model": SMART_AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
        **_llm_token_limit(500),
    }
    response = _request_with_429_retry(
        requests.post,
        "إنشاء الرد الذكي",
        f"{SMART_AI_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {SMART_AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
        retries=1,
        retry_base=0.2,
    )
    response.raise_for_status()
    result = response.json()
    reply = (result.get("choices", [{}])[0].get("message", {}).get("content") or "").strip() or None
    event_id = active_message_events.get(sender)
    if event_id:
        update_message_event(
            event_id,
            ai_model=SMART_AI_MODEL,
            ai_status="success" if reply else "empty",
            ai_result=reply or "",
        )
    return reply


IMAGE_MATCH_MIN_CONFIDENCE = 0.60


def resolve_image_product_match(result, products):
    """مطابقة نتيجة النموذج مع الكتالوج حتى عند غياب المعرف أو انخفاض الثقة قليلاً."""
    if not result:
        return None
    matched_id = result.get("matched_product_id")
    confidence = float(result.get("confidence") or 0)
    if matched_id is not None and confidence >= IMAGE_MATCH_MIN_CONFIDENCE:
        try:
            matched_id = int(matched_id)
        except (TypeError, ValueError):
            matched_id = None
        if matched_id is not None:
            product = next((p for p in products if int(p.get("id") or -1) == matched_id), None)
            if product:
                return product
            product = get_product(matched_id)
            if product:
                return product

    candidate_text = normalize_text(
        " ".join(
            str(result.get(key) or "")
            for key in ("matched_product_name", "extracted_text", "brand", "visual_description")
        )
    )
    if not candidate_text:
        candidate_text = normalize_text(str(result.get("reply") or ""))
    if not candidate_text:
        return None
    candidate_tokens = {token for token in candidate_text.split() if len(token) >= 3}
    scored_products = []
    for product in products:
        aliases = [product.get("name", "")]
        aliases.extend((product.get("keywords", "") or "").split(","))
        for alias in aliases:
            alias_normalized = normalize_text(alias)
            if len(alias_normalized) >= 4 and alias_normalized in candidate_text:
                return product
            alias_tokens = {token for token in alias_normalized.split() if len(token) >= 3}
            if alias_tokens and candidate_tokens:
                overlap = len(alias_tokens & candidate_tokens) / min(len(alias_tokens), len(candidate_tokens))
                if overlap >= 0.5:
                    scored_products.append((overlap, product))
                    break
    scored_products.sort(key=lambda item: item[0], reverse=True)
    if scored_products:
        best_score, best_product = scored_products[0]
        second_score = scored_products[1][0] if len(scored_products) > 1 else 0
        if best_score >= 0.75 or best_score - second_score >= 0.2:
            return best_product
    return None


def resolve_image_variant_match(result, product):
    """إرجاع خيار المنتج عندما يظهر موديله بوضوح في تحليل الصورة."""
    if not result or not isinstance(product, dict):
        return None
    evidence = " ".join(
        str(result.get(key) or "")
        for key in ("detected_model", "extracted_text", "matched_product_name", "visual_description")
    )
    compact_evidence = re.sub(r"[^a-z0-9]", "", evidence.lower())
    if not compact_evidence:
        return None
    for index, variant in enumerate(product_variants(product)):
        variant_name = str(variant.get("name") or variant.get("label") or "")
        model_match = re.search(r"\b(?:md|model)[\s_-]*[a-z0-9]+\b", variant_name, re.IGNORECASE)
        if not model_match:
            continue
        compact_model = re.sub(r"[^a-z0-9]", "", model_match.group(0).lower())
        if compact_model and compact_model in compact_evidence:
            return {"index": index, "variant": variant}
    return None


def notify_owner_uncertain_product_image(sender, image_id="", caption=""):
    """تنبيه الإدارة بصورة تحتاج مطابقة دون وصفها خطأً بأنها غير متوفرة."""
    send_message(
        OWNER_NUMBER,
        "📸 صورة منتج تحتاج مطابقة يدوية\n"
        f"👤 العميل: {sender}\n"
        f"📝 الكابشن: {caption or 'لا يوجد'}\n"
        "لم يتم اعتبار المنتج غير متوفر تلقائياً.",
    )
    if image_id:
        send_image_by_id(OWNER_NUMBER, image_id, "صورة منتج تحتاج مطابقة")


def _product_image_urls(product):
    raw_urls = product.get("image_urls") or []
    if isinstance(raw_urls, str):
        try:
            raw_urls = json.loads(raw_urls)
        except (TypeError, ValueError):
            raw_urls = [raw_urls] if raw_urls.startswith("http") else []
    if not isinstance(raw_urls, list):
        return []
    return [str(url).strip() for url in raw_urls if str(url).strip().startswith("http")]


def _catalog_image_fingerprint(image_bytes):
    """بصمة مقاومة لتغيير الحجم والضغط للصورة المحوّلة من القناة."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = ImageOps.fit(image, (24, 24), method=Image.Resampling.LANCZOS)
    gray = image.convert("L")
    pixels = list(gray.getdata())
    average = sum(pixels) / max(len(pixels), 1)
    average_hash = tuple(pixel >= average for pixel in pixels)
    differences = tuple(
        gray.getpixel((x, y)) >= gray.getpixel((x - 1, y))
        for y in range(24)
        for x in range(1, 24)
    )
    color_buckets = tuple(
        round(sum(image.getpixel((x, y))[channel] for x in range(24) for y in range(24)) / (24 * 24) / 16)
        for channel in range(3)
    )
    return average_hash, differences, color_buckets


def _catalog_image_similarity(left, right):
    if not left or not right:
        return 0.0
    left_average, left_diff, left_colors = left
    right_average, right_diff, right_colors = right
    average_score = sum(a == b for a, b in zip(left_average, right_average)) / len(left_average)
    difference_score = sum(a == b for a, b in zip(left_diff, right_diff)) / len(left_diff)
    color_score = sum(abs(a - b) <= 1 for a, b in zip(left_colors, right_colors)) / len(left_colors)
    return average_score * 0.45 + difference_score * 0.4 + color_score * 0.15


def _download_catalog_image(url):
    cached = catalog_image_fingerprint_cache.get(url)
    if cached is not None:
        return cached
    try:
        response = requests.get(url, timeout=CATALOG_IMAGE_TIMEOUT)
        response.raise_for_status()
        fingerprint = _catalog_image_fingerprint(response.content)
        catalog_image_fingerprint_cache[url] = fingerprint
        return fingerprint
    except Exception as exc:
        print(f"[مطابقة الصور] تعذر تنزيل صورة الكتالوج: {url} — {exc}")
        catalog_image_fingerprint_cache[url] = False
        return None


def match_image_against_catalog(image_bytes, products):
    """مطابقة الصورة بدون اسم مع الصور، أو إرجاع أفضل مرشح فئوي عند اختلاف الموديل."""
    try:
        incoming = _catalog_image_fingerprint(image_bytes)
    except Exception as exc:
        print(f"[مطابقة الصور] تعذر استخراج بصمة الصورة الواردة: {exc}")
        return None
    candidates = [(product, url) for product in (products or []) for url in _product_image_urls(product)]
    if not candidates:
        return None
    with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as executor:
        fingerprints = executor.map(lambda item: _download_catalog_image(item[1]), candidates)
        scored = [
            (_catalog_image_similarity(incoming, fingerprint), product)
            for (product, _), fingerprint in zip(candidates, fingerprints)
            if fingerprint
        ]
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < CATALOG_IMAGE_FAMILY_THRESHOLD:
        return None
    best_score, best_product = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score >= 0.94 or best_score - second_score >= 0.08:
        print(f"[مطابقة الصور] تطابق محلي {best_product.get('name')} بنسبة {best_score:.2f}")
        return {"product": best_product, "match_type": "exact", "score": best_score}
    if best_score >= CATALOG_IMAGE_MATCH_THRESHOLD:
        print(f"[مطابقة الفئة] موديل قريب من {best_product.get('name')} بنسبة {best_score:.2f}")
        return {"product": best_product, "match_type": "family", "score": best_score}
    return None


def analyze_product_image(sender, message, caption=""):
    """تحليل صورة العميل ومطابقتها مع المنتجات دون اعتبار إثبات الدفع منتجاً."""
    if not SMART_AI_API_KEY:
        return None
    products = get_all_products()[:60]
    caption_matches = match_products_from_text(caption, products)
    if caption_matches:
        return {"kind": "product_family", "products": caption_matches}
    image_bytes, mime_type = download_whatsapp_image(message.get("image", {}))
    local_match = match_image_against_catalog(image_bytes, products)
    if local_match:
        return {
            "kind": "product",
            "product": local_match["product"],
            "match_method": f"local_{local_match['match_type']}",
        }
    image_data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    product_context = "\n".join(
        f"ID={p.get('id')}; الاسم={p.get('name', '')}; الكلمات={p.get('keywords', '')}; "
        f"السعر={p.get('price', 0)} ريال; الخيارات={p.get('variants', '')}; الوصف={p.get('description', '')}"
        for p in products
    ) or "لا توجد منتجات محفوظة حالياً."
    forwarded = bool((message.get("context") or {}).get("forwarded"))
    forwarded_hint = (
        "هذه الصورة محوّلة من قناة أو محادثة أخرى؛ اعتبريها صورة منتج مرجعية، "
        "واستخدمي الاسم أو الشكل أو العلامة الظاهرة لمطابقتها مع الكتالوج.\n"
        if forwarded
        else ""
    )
    user_text = (
        "حلل صورة العميل بدقة متعددة المراحل. استخرجي النص الظاهر والعلامة التجارية ورقم الموديل "
        "ووصفاً بصرياً مختصراً للون والشكل والخامة والاستخدام. إذا كانت الصورة إيصال تحويل أو كشفاً مالياً فاجعل "
        "is_payment_proof=true ولا تطابقها مع منتج. إذا كانت صورة منتج، طابقها فقط "
        "مع منتج من القائمة، ويمكن قبول مطابقة معقولة إذا كان الشكل أو الاسم أو العلامة "
        "متوافقاً. لا تخترع اسماً أو سعراً. "
        f"{forwarded_hint}كابشن العميل إن وجد: {caption or 'لا يوجد'}\n\nالمنتجات المتاحة:\n{product_context}"
    )
    payload = {
        "model": SMART_AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "أنت محللة صور دقيقة لمتجر Titiz للأدوات المنزلية. أجيبي بنتيجة JSON فقط. "
                    "اقرئي أي نص أو شعار أو رقم موديل ظاهر، وصفي اللون والشكل والخامة والاستخدام، "
                    "ضعي رقم الموديل الظاهر في detected_model كما هو، مثل MD-5266، أو اتركيه فارغاً إذا لم يظهر. "
                    "ثم قارني هذه الإشارات مع أسماء وكلمات ووصف المنتجات في الكتالوج، ولا تشترطي كابشن؛ "
                    "الصورة المحوّلة من القناة قد تصل بدون كابشن. "
                    "عند عدم التأكد الشديد اجعلي matched_product_id=null وconfidence=0، "
                    "واكتبي رداً عربياً قصيراً يطلب اسم المنتج أو صورة أوضح."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url, "detail": "auto"}},
                ],
            },
        ],
        "temperature": 0.1,
        **_llm_token_limit(350),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "product_image_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "is_product_like": {"type": "boolean"},
                        "is_payment_proof": {"type": "boolean"},
                        "matched_product_id": {"type": ["integer", "null"]},
                        "matched_product_name": {"type": "string"},
                        "detected_model": {"type": "string"},
                        "extracted_text": {"type": "string"},
                        "brand": {"type": "string"},
                        "visual_description": {"type": "string"},
                        "confidence": {"type": "number"},
                        "reply": {"type": "string"},
                    },
                    "required": [
                        "is_product_like",
                        "is_payment_proof",
                        "matched_product_id",
                        "matched_product_name",
                        "detected_model",
                        "extracted_text",
                        "brand",
                        "visual_description",
                        "confidence",
                        "reply",
                    ],
                    "additionalProperties": False,
                },
            },
        },
    }
    response = _request_with_429_retry(
        requests.post,
        "تحليل صورة المنتج",
        f"{SMART_AI_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {SMART_AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=IMAGE_REQUEST_TIMEOUT,
        retries=IMAGE_MAX_RETRIES,
        retry_base=IMAGE_RETRY_BASE_SECONDS,
    )
    response.raise_for_status()
    content = response.json().get("choices", [{}])[0].get("message", {}).get("content") or "{}"
    result = json.loads(content)
    if result.get("is_payment_proof"):
        return {
            "kind": "payment_proof",
            "reply": "📄 هذه الصورة تبدو كإشعار تحويل. إذا كنتِ تريدين إكمال الدفع، أرسليها بعد اختيار التحويل المسبق من الطلب 😊",
        }
    product = resolve_image_product_match(result, products)
    if product:
        variant_match = resolve_image_variant_match(result, product)
        return {"kind": "product", "product": product, "variant_match": variant_match}
    
    # حماية إضافية: إذا كان النموذج قد طابق اسماً في الرد أو الملاحظات ولكن لم يمر عبر المعرف
    reply_text = str(result.get("reply") or "")
    matched_name = str(result.get("matched_product_name") or "")
    for candidate in products:
        name_norm = normalize_text(candidate.get("name", ""))
        if (matched_name and name_norm in normalize_text(matched_name)) or (reply_text and name_norm in normalize_text(reply_text)):
            return {"kind": "product", "product": candidate, "variant_match": None}

    return {"kind": "unknown", "reply": result.get("reply") or "🔍 لم أتمكن من تحديد المنتج بدقة. أرسلي صورة أوضح أو اكتبي اسم المنتج من فضلكِ 😊"}

def deliver_pending_replies(to):
    """إرسال ردود الإدارة المؤجلة بعد أن يبدأ العميل محادثته."""
    if not to or to == OWNER_NUMBER:
        return
    for pending in get_pending_replies(to):
        if send_message(to, pending["message"]):
            mark_pending_reply_sent(pending["id"])

def send_image(to, image_url, caption=""):
    _send_voice_reply_if_needed(to, caption)
    result = whatsapp.send_image(to, image_url, caption)
    if result:
        _record_outbound_event(to, "image", caption, image_url)
    return result

def send_image_by_id(to, media_id, caption=""):
    _send_voice_reply_if_needed(to, caption)
    result = whatsapp.send_image_by_id(to, media_id, caption)
    if result:
        _record_outbound_event(to, "image", caption, media_id)
    return result


def send_admin_share_card(product, image_id=""):
    """إرسال بطاقة منتج مكتملة لرقم الإدارة كي يشاركها يدوياً بأمان."""
    if not isinstance(product, dict):
        return False
    product = canonicalize_product(product)
    body = (
        "📣 *بطاقة جاهزة للنشر*\n\n"
        f"{format_product_card(product)}\n\n"
        "↗️ شاركي هذه البطاقة مع قناة Titiz أو مجموعة العروض."
    )
    if image_id:
        return send_image_by_id(OWNER_NUMBER, image_id, body)
    image_urls = _product_image_urls(product)
    if image_urls:
        return send_image(OWNER_NUMBER, image_urls[0], body)
    return send_message(OWNER_NUMBER, body)

def send_buttons(to, text, buttons):
    _send_voice_reply_if_needed(to, text)
    result = whatsapp.send_buttons(to, text, buttons)
    if result:
        _record_outbound_event(to, "interactive_buttons", text)
    return result


def send_carousel(to, text, cards):
    _send_voice_reply_if_needed(to, text)
    result = whatsapp.send_carousel(to, text, cards)
    if result:
        _record_outbound_event(to, "interactive_carousel", text)
    return result


def product_variants(product):
    raw_variants = product.get("variants", "")
    if isinstance(raw_variants, str):
        if not raw_variants.startswith("["):
            return []
        try:
            raw_variants = json.loads(raw_variants)
        except json.JSONDecodeError:
            return []
    return raw_variants if isinstance(raw_variants, list) else []


def remember_variant_context(to, product):
    """حفظ آخر منتج متعدد الخيارات لدعم الأجهزة التي تعيد عنوان الزر بدلاً من المعرف."""
    if not isinstance(product, dict) or not product_variants(product):
        return
    try:
        product_id = int(product.get("id"))
    except (TypeError, ValueError):
        return
    variant_button_context[to] = {
        "product_id": product_id,
        "expires_at": time.time() + VARIANT_CONTEXT_WINDOW,
    }


def get_variant_context_product(to):
    """استعادة المنتج المرتبط بزر اختيار الحجم خلال مدة قصيرة وآمنة."""
    context = variant_button_context.get(to) or {}
    if context.get("expires_at", 0) < time.time():
        variant_button_context.pop(to, None)
        return None
    product = get_product(context.get("product_id"))
    return canonicalize_product(product) if product else None


def send_variant_list(to, product):
    """عرض أحجام المنتج وأسعارها في قائمة واتساب قابلة للاختيار."""
    rows = []
    for index, variant in enumerate(product_variants(product)):
        label = str(variant.get("name") or variant.get("label") or "الخيار")
        price = parse_product_price(variant.get("price"))
        if price is None:
            continue
        rows.append({
            "id": f"variant_{product['id']}_{index}",
            "title": f"{label} - {int(price)} ريال"[:24],
            "description": "اختيار هذا الحجم والسعر",
        })
    if rows:
        send_list(to, "اختاري الحجم والسعر المناسب:", "اختيار الحجم", [{
            "title": "الأحجام المتوفرة",
            "rows": rows[:10],
        }])

def send_welcome(to):
    """إرسال الترحيب الجديد مع أزرار الوصول السريع."""
    send_buttons(to, WELCOME_MESSAGE, [
        {"id": "browse_products", "title": "🛍️ المنتجات"},
        {"id": "menu_cart", "title": "🛒 السلة"},
        {"id": "menu_orders", "title": "📦 طلباتي"},
    ])


def send_guided_help(to, intro=""):
    """رد اجتماعي ودود مع قائمة Titiz بدون افتراض أن العميل يبحث عن منتج."""
    body = (intro.strip() + "\n\n" if intro and intro.strip() else "") + GUIDED_HELP_MESSAGE
    send_list(to, body, "اختاري الخدمة", [{
        "title": "كيف أساعدك؟",
        "rows": [
            {"id": "menu_search", "title": "🔍 البحث عن منتج", "description": "اكتبي الاسم أو صفي المنتج"},
            {"id": "menu_cart", "title": "🛒 السلة", "description": "عرض المنتجات التي اخترتها"},
            {"id": "menu_orders", "title": "📦 طلباتي", "description": "متابعة طلباتك وحالتها"},
            {"id": "menu_offers", "title": "🎁 العروض", "description": "قناة التخفيضات والخصومات"},
            {"id": "menu_contact", "title": "📞 التواصل مع المندوبة", "description": "مساعدة مباشرة"},
        ],
    }])


def is_social_or_confused_message(normalized_text):
    return normalized_text in {normalize_text(item) for item in SOCIAL_OR_CONFUSED_PHRASES}


def is_search_examples_request(normalized_text):
    """تمييز سؤال العميل عن أمثلة للبحث كي لا يُفسر كطلب منتج."""
    examples_phrases = {
        "مثل ايش اكتب", "مثلا ايش اكتب", "مثال ايش اكتب", "كيف اكتب",
        "كيف ابحث", "ايش اكتب", "وش اكتب", "ما الذي اكتب", "ماذا اكتب",
        "اعطيني مثال", "عطيني مثال", "هات مثال", "ابغى مثال",
        "وش اكتب لكم", "ايش اكتب لكم", "ما هي الامثله", "ماهي الامثله",
    }
    return normalized_text in {normalize_text(item) for item in examples_phrases}


def send_search_examples(to):
    """إرسال أمثلة كتابة فقط، دون تشغيل البحث أو عرض بطاقات منتجات."""
    send_message(
        to,
        "اكتبي اسم المنتج أو حتى كلمة منه 😊\n\n"
        "*مثلاً:*\n"
        "☕ كتلي شاي\n"
        "🍽️ صحون فرم\n"
        "🧺 سلال رحلات\n"
        "🥣 حافظات أبو قفل\n"
        "🥛 اقلاص شاي\n\n"
        "وإذا ما تعرفي الاسم، وصفيه لي مثل: *صحن زجاج كبير* أو *مفتاح غاز*، وسأبحث لكِ عنه فوراً."
    )


def is_positive_social_message(normalized_text):
    """تمييز المدح والقبول القصير عن سؤال السعر أو طلب التخفيض."""
    return normalized_text in {normalize_text(item) for item in POSITIVE_SOCIAL_PHRASES}


def send_contextual_praise_reply(to):
    """رد واحد قصير للمدح، مع متابعة المنتج نفسه إن كان موجوداً في السياق."""
    context = user_sessions.get(to, {})
    last_product = context.get("last_product") if isinstance(context, dict) else None
    if isinstance(last_product, dict) and last_product.get("id") and last_product.get("name"):
        variants = product_variants(last_product)
        valid_variants = [v for v in variants if parse_product_price(v.get("price")) is not None]
        primary_button = (
            {"id": f"variants_{last_product['id']}", "title": "📏 اختيار الحجم"}
            if valid_variants
            else {"id": f"add_{last_product['id']}", "title": "🛒 إضافة للسلة"}
        )
        send_buttons(
            to,
            f"يسعدنا إنه عجبكِ *{last_product['name']}* يا غالية 😊\nهل تحبين نكمل عليه أو تبحثين عن شيء ثاني؟",
            [
                primary_button,
                {"id": f"det_{last_product['id']}", "title": "📋 التفاصيل"},
                {"id": "shopping_assistant", "title": "🔍 بحث عن منتج"},
            ],
        )
        return
    send_list(to, "يسعدنا إن Titiz نال إعجابكِ يا غالية 😊\nقولي لي ما الذي تبحثين عنه وسأساعدكِ خطوة بخطوة.", "ابدئي الآن", [{
        "title": "اختاري ما تحتاجينه",
        "rows": [
            {"id": "menu_search", "title": "🔍 البحث عن منتج", "description": "اكتبي الاسم أو صفي المنتج"},
            {"id": "menu_cart", "title": "🛒 السلة", "description": "عرض المنتجات التي اخترتها"},
            {"id": "menu_orders", "title": "📦 طلباتي", "description": "متابعة الطلبات والحالة"},
            {"id": "menu_offers", "title": "🎁 العروض", "description": "قناة التخفيضات والخصومات"},
        ],
    }])


def send_product_request_menu(to):
    """طلب اسم المنتج في رسالة واحدة قابلة للتنفيذ دون تكرار سؤال عام."""
    send_buttons(
        to,
        "أبشري يا غالية 😊 اكتبي اسم الأداة التي تريدينها، أو اختاري الفئة وسأبحث لكِ فوراً.",
        [
            {"id": "category_kitchen", "title": "🍳 أدوات مطبخ"},
            {"id": "category_electronics", "title": "⚡ إلكترونيات"},
            {"id": "category_cleaning", "title": "🧼 منظفات"},
        ],
    )


def is_frustration_or_confusion_message(normalized_text):
    normalized_phrases = {normalize_text(item) for item in FRUSTRATION_OR_CONFUSION_PHRASES}
    return any(phrase == normalized_text or phrase in normalized_text for phrase in normalized_phrases)


def send_conversational_recovery(to, msg_normalized, semantic_result=None):
    """اختيار رد مهني واحد للرسالة غير المكتملة بدلاً من تكرار التوضيح القديم."""
    semantic_intent = str((semantic_result or {}).get("intent") or "").strip()
    if semantic_intent in {"product_search", "product_purchase", "product_choice"}:
        send_product_request_menu(to)
        return
    if is_frustration_or_confusion_message(msg_normalized):
        send_guided_help(
            to,
            "حقك علي يا غالية 😊 ما أبغى أكرر عليكِ. قولي لي تبغين منتج، سلة، طلب، أو عروض وسأمشي معكِ مباشرة.",
        )
        return
    send_guided_help(to, "أنا معك يا غالية 😊 اختاري الخدمة المناسبة أو اكتبي طلبك بطريقتك.")


_catalog_metadata_cache = None


def canonicalize_product(product):
    """توحيد بيانات البطاقة من products.json لمنع بقاء صورة قديمة في SQLite."""
    global _catalog_metadata_cache
    if not isinstance(product, dict):
        return product
    if _catalog_metadata_cache is None:
        try:
            with open(os.path.join(os.path.dirname(__file__), "products.json"), encoding="utf-8") as handle:
                raw_catalog = json.load(handle)
            _catalog_metadata_cache = {
                normalize_text(str(name)): info
                for name, info in raw_catalog.items()
                if isinstance(info, dict)
            }
        except (OSError, json.JSONDecodeError):
            _catalog_metadata_cache = {}
    catalog_entry = _catalog_metadata_cache.get(normalize_text(str(product.get("name", ""))))
    if not catalog_entry:
        return product
    merged = dict(product)
    for field in ("price", "description", "keywords", "image_id", "image_urls", "variants"):
        if field in catalog_entry:
            merged[field] = catalog_entry[field]
    return merged


def send_product_card(to, product):
    """إرسال صورة المنتج وحدها ثم وصفه وأزراره بمعرفات لا تتكرر."""
    product = canonicalize_product(product)
    guard_key = (to, int(product.get("id", 0)))
    now = time.time()
    if now - product_send_guard.get(guard_key, 0) < PRODUCT_SEND_WINDOW:
        print(f"[تجاهل تكرار المنتج] {guard_key}")
        return False
    product_send_guard[guard_key] = now
    product_reply = format_product_card(product)
    variants = product_variants(product)
    valid_variants = [v for v in variants if parse_product_price(v.get("price")) is not None]
    base_price = parse_product_price(product.get("price"))
    if not valid_variants and base_price is None:
        send_message(to, "⚠️ هذا المنتج غير متاح حالياً لأن سعره غير محدد.")
        return False
    user_states[to] = "product_context"
    user_sessions[to] = {"last_product": product}
    if valid_variants:
        remember_variant_context(to, product)
    raw_image_urls = product.get("image_urls", "")
    if isinstance(raw_image_urls, str):
        try:
            image_urls = json.loads(raw_image_urls) if raw_image_urls.startswith("[") else []
        except json.JSONDecodeError:
            image_urls = []
    else:
        image_urls = raw_image_urls or []
    # بطاقة المنتج المختار يجب أن تسلك مساراً واحداً ثابتاً. الكاروسيل مناسب
    # لنتائج البحث المتعددة، لكنه يكرر نفس المنتج ويجعل ضغطات الحجم غير ثابتة.
    # لذلك نعرض صورة واحدة مع قائمة الأحجام الأصلية من واتساب.
    image_id = product.get("image_id", "")
    if image_id:
        send_image_by_id(to, image_id)
    elif image_urls:
        send_image(to, image_urls[0])
    if valid_variants:
        send_message(to, product_reply)
        send_variant_list(to, product)
        schedule_product_followup(to, product.get("name", ""))
        return True
    sent = send_buttons(to, product_reply, [
        {"id": f"add_{product['id']}", "title": "🛒 إضافة للسلة"},
        {"id": f"det_{product['id']}", "title": "📋 تفاصيل المنتج"},
        {"id": "shopping_assistant", "title": "🔙 متابعة التسوق"},
    ])
    schedule_product_followup(to, product.get("name", ""))
    return bool(sent)


def send_matched_product_variant_card(to, product, variant_match):
    """عرض نفس المنتج مع خيار الموديل الظاهر في صورة العميل فقط."""
    product = canonicalize_product(product)
    variant_index = int((variant_match or {}).get("index", -1))
    variants = product_variants(product)
    if not (0 <= variant_index < len(variants)):
        return send_product_card(to, product)
    variant = variants[variant_index]
    price = parse_product_price(variant.get("price"))
    if price is None:
        return send_product_card(to, product)

    user_states[to] = "product_context"
    previous = user_sessions.get(to, {})
    previous = previous if isinstance(previous, dict) else {}
    user_sessions[to] = {**previous, "last_product": product, "matched_variant_index": variant_index}
    remember_variant_context(to, product)

    image_urls = _product_image_urls(product)
    if image_urls:
        send_image(to, image_urls[0])
    elif product.get("image_id"):
        send_image_by_id(to, product["image_id"])

    variant_name = str(variant.get("name") or variant.get("label") or "الخيار الظاهر")
    send_buttons(
        to,
        f"✅ لقيت نفس المنتج عندنا: *{product.get('name', 'المنتج')}*\n"
        f"🎯 الموديل/الحجم الظاهر: *{variant_name}*\n"
        f"💰 السعر: *{int(price)} ريال*\n\n"
        "تقدرين تضيفين هذا الخيار مباشرة أو تختارين حجماً آخر 😊",
        [
            {"id": f"variant_{product['id']}_{variant_index}", "title": "🛒 إضافة هذا الحجم"},
            {"id": f"variants_{product['id']}", "title": "📏 اختيار حجم آخر"},
            {"id": "menu_cart", "title": "🛍️ عرض السلة"},
        ],
    )
    schedule_product_followup(to, product.get("name", ""))
    return True


RELATED_PRODUCT_STOPWORDS = {
    "اصلي", "الاصلي", "اصلية", "الاصلية", "ضمان", "منتجات", "المائدة", "المائده",
    "الدار", "التاج", "الملكي", "الملكية", "ملك", "ابو", "كبير", "صغير", "وسط",
    "مدور", "مربع", "هندي", "مفتوح", "برمه", "حجم", "حبات", "قطعة", "قطع",
}

PRODUCT_FAMILY_HINTS = {
    "tea_cooler": {"ثلاجة", "ثلاجات", "ثلاجه", "تبريد", "ثلاجات شاي"},
    "juicer": {"عصارة", "عصارات", "عصير", "حمضيات"},
    "peeler": {"مقشرة", "مقرشة", "بطاط", "تقشير"},
    "pots": {"قدر", "قدور", "حلل", "طنجرة", "طناجر", "برمة"},
    "scrubber": {"سلك", "مواعين", "جلي", "ليفة"},
    "kettle": {"كتلي", "غلاية", "صفارة", "غلايه"},
}


def _product_family(text):
    normalized = normalize_text(text)
    scores = {
        family: sum(1 for hint in hints if hint in normalized)
        for family, hints in PRODUCT_FAMILY_HINTS.items()
    }
    family, score = max(scores.items(), key=lambda item: item[1])
    return family if score else None


def _family_token(token):
    token = normalize_text(token)
    return token[:5] if len(token) >= 5 else token


def products_related_to_image(product, products):
    """تجميع منتجات الفئة نفسها، مثل كل ثلاجات الشاي، من المنتج الذي طابقته الصورة."""
    if not isinstance(product, dict):
        return []
    seed_text = " ".join([
        str(product.get("name") or ""),
        str(product.get("keywords") or ""),
        str(product.get("description") or ""),
    ])
    seed_tokens = {
        _family_token(token)
        for token in normalize_text(seed_text).replace(",", " ").split()
        if len(token) >= 3 and token not in RELATED_PRODUCT_STOPWORDS
    }
    seed_family = _product_family(seed_text)
    if not seed_tokens:
        return [product]
    scored = []
    for candidate in products:
        candidate_text = " ".join([
            str(candidate.get("name") or ""),
            str(candidate.get("keywords") or ""),
            str(candidate.get("description") or ""),
        ])
        candidate_family = _product_family(candidate_text)
        if seed_family and candidate_family != seed_family:
            continue
        candidate_tokens = {
            _family_token(token)
            for token in normalize_text(candidate_text).replace(",", " ").split()
            if len(token) >= 3 and token not in RELATED_PRODUCT_STOPWORDS
        }
        overlap = len(seed_tokens & candidate_tokens)
        if overlap:
            scored.append((overlap, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    related = [candidate for _, candidate in scored]
    return related or [product]


def send_matching_products_carousel(to, products, query_key=""):
    """إرسال نتائج البحث في بطاقات واتساب أفقية، مع fallback آمن عند رفض الكاروسيل."""
    guard_key = (to, normalize_text(query_key or ""))
    now = time.time()
    if query_key and now - matching_send_guard.get(guard_key, 0) < MATCHING_SEND_WINDOW:
        print(f"[تجاهل تكرار نتائج البحث] {guard_key}")
        return True

    unique_products = []
    seen_product_keys = set()
    for product in products:
        product = canonicalize_product(product)
        product_key = product.get("id") or normalize_text(product.get("name", ""))
        if product_key in seen_product_keys:
            continue
        seen_product_keys.add(product_key)
        unique_products.append(product)

    if not unique_products:
        return False

    current_session = user_sessions.get(to, {})
    current_session = current_session if isinstance(current_session, dict) else {}
    user_sessions[to] = {**current_session, "last_product": unique_products[0]}
    user_states[to] = "product_context"

    variant_products = [
        product for product in unique_products
        if any(parse_product_price(v.get("price")) is not None for v in product_variants(product))
    ]
    if len(variant_products) == 1:
        remember_variant_context(to, variant_products[0])

    cards = []
    for product in unique_products[:10]:
        image_urls = _product_image_urls(product)
        if not image_urls:
            continue
        valid_variants = [
            v for v in product_variants(product)
            if parse_product_price(v.get("price")) is not None
        ]
        if not valid_variants and parse_product_price(product.get("price")) is None:
            continue
        buttons = [{"id": f"det_{product['id']}", "title": "📋 التفاصيل"}]
        if valid_variants:
            buttons.insert(0, {"id": f"variants_{product['id']}", "title": "📏 اختيار الحجم"})
        else:
            buttons.insert(0, {"id": f"add_{product['id']}", "title": "🛒 إضافة للسلة"})
        cards.append({
            "image_url": image_urls[0],
            "body": format_product_card(product, compact=True),
            "buttons": buttons,
        })

    query_label = " ".join(str(query_key or "المنتجات").split())[:45] or "المنتجات"
    intro_text = (
        f"🔍 لقيت لكِ خيارات مشابهة من *{query_label}* 😊\n\n"
        "هذه المنتجات تأتي بأشكال وأسعار مختلفة لتختاري الأنسب لاستخدامكِ.\n"
        "شاهدي الصور والوصف والسعر، ثم اختاري الحجم أو أضيفي المنتج للسلة."
    )
    delegate_text = (
        "هل تريد التأكد من حصولك على أفضل سعر؟ لا يزال بإمكانك التواصل مباشرة "
        "مع مندوبة Titiz إذا أعجبك عرضها."
    )

    send_message(to, intro_text)
    # الكاروسيل يحتاج من بطاقتين إلى عشر بطاقات، وكل بطاقة يجب أن تحمل نفس نوع
    # وعدد أزرار الرد السريع. send_carousel يطبق هذه البنية الرسمية.
    if len(cards) >= 2 and send_carousel(to, "🛍️ اسحبي لمشاهدة المنتجات:", cards[:10]):
        matching_send_guard[guard_key] = now
        schedule_product_followup(to, unique_products[0].get("name", ""))
        if not whatsapp.send_url_button(
            to,
            delegate_text,
            "📞 التواصل مع المندوبة",
            DELEGATE_WHATSAPP_URL,
        ):
            send_message(to, delegate_text + f"\n\n📞 {DELEGATE_WHATSAPP_URL}")
        return True

    # إذا رفض واتساب الكاروسيل أو بقيت نتيجة واحدة، نستخدم البطاقة الفردية
    # الموثوقة، لكن لا نرسل رسالة التواصل إلا بعد نجاح بطاقة واحدة على الأقل.
    sent_cards = 0
    for product in unique_products[:10]:
        if send_product_card(to, product):
            sent_cards += 1

    if sent_cards:
        matching_send_guard[guard_key] = now
        schedule_product_followup(to, unique_products[0].get("name", ""))
        if not whatsapp.send_url_button(
            to,
            delegate_text,
            "📞 التواصل مع المندوبة",
            DELEGATE_WHATSAPP_URL,
        ):
            send_message(to, delegate_text + f"\n\n📞 {DELEGATE_WHATSAPP_URL}")
        return True

    return False

def send_list(to, text, button_text, sections):
    _send_voice_reply_if_needed(to, text)
    result = whatsapp.send_list(to, text, button_text, sections)
    if result:
        _record_outbound_event(to, "interactive_list", text)
    return result

def notify_owner(sender, msg_body, message_event_id=None):
    """إرسال كل رسالة عميل للإدارة في بطاقة نصية موحدة وسهلة القراءة، وتخزين ربط wamid الإدارة برقم العميل."""
    customer = get_customer(sender) or {}
    customer_name = str(customer.get("name") or "").strip() or "غير مسجل"
    now = datetime.now(YEMEN_TIMEZONE).strftime("%d-%m-%Y، %H:%M")
    sequence_number = reserve_owner_notification_sequence(sender, message_event_id)
    message_reference = f"{sequence_number:04d}" if sequence_number else "غير متاح"
    notification = (
        "📨 *رسالة جديدة*\n"
        "━━━━━━━━━━━━\n"
        f"👤 العميل: {customer_name}\n"
        f"📞 الرقم: {sender}\n"
        f"💬 الرسالة:\n{msg_body}\n"
        f"🕒 التاريخ والوقت: {now}\n"
        f"🆔 رقم الرسالة: {message_reference}\n"
        "━━━━━━━━━━━━"
    )
    res = send_message(OWNER_NUMBER, notification)
    # إذا أعادت send_message معرف رسالة واتساب (wamid) حقيقي، نسجله في الأحداث لكي يعمل الرد المقتبس 100%
    if res and isinstance(res, str) and res.startswith("wamid."):
        record_message_event(
            whatsapp_message_id=res,
            direction="outbound",
            phone_number=sender,
            message_type="text",
            body=notification,
        )


def notify_owner_unavailable_product(sender, request_text, source="text", image_id=""):
    """إبلاغ الإدارة بطلب منتج غير موجود حتى يمكن توفيره لاحقاً."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_label = "صورة" if source == "image" else "كلمة"
    notification = (
        "📦 *طلب منتج غير متوفر*\n\n"
        f"👤 رقم العميل: {sender}\n"
        f"🔎 المصدر: {source_label}\n"
        f"📝 طلب العميل: {request_text or 'صورة منتج غير واضحة'}\n"
        f"🕐 الوقت: {now}\n\n"
        "يرجى مراجعة الطلب ومحاولة توفير المنتج."
    )
    send_message(OWNER_NUMBER, notification)
    if image_id:
        send_image_by_id(OWNER_NUMBER, image_id, "🖼️ صورة المنتج المطلوب غير المتوفر")


UNAVAILABLE_IMAGE_RESPONSE = (
    "تم ارسال طلبك للاداره سيتم توفير المنتج وسيتم الرد عليك خلال دقاق"
)


def send_unavailable_image_response(to):
    """إبلاغ العميل بلطف مع زر مباشر للمندوبة عند عدم مطابقة صورة المنتج."""
    if not whatsapp.send_url_button(
        to,
        UNAVAILABLE_IMAGE_RESPONSE,
        "📞 التواصل مع المندوبة",
        DELEGATE_WHATSAPP_URL,
    ):
        send_message(
            to,
            UNAVAILABLE_IMAGE_RESPONSE + f"\n\n📞 التواصل مع المندوبة:\n{DELEGATE_WHATSAPP_URL}",
        )

def notify_owner_new_order(order_number, phone, name, address, items, total, payment_method):
    items_text = ""
    for item in items:
        items_text += f"  • {item['name']} × {item.get('qty',1)} = {item.get('total',0)} ريال\n"
    msg = f"🔔 *طلب جديد!*\n\n📋 رقم الطلب: *{order_number}*\n👤 الاسم: {name}\n📱 الرقم: {phone}\n📍 العنوان: {address}\n\n🛒 *المنتجات:*\n{items_text}\n💰 *الإجمالي: {int(total)} ريال*\n💳 الدفع: {payment_method}"
    send_buttons(OWNER_NUMBER, msg, [
        {"id": f"admin_prep_{order_number}", "title": "✅ تم التجهيز"},
        {"id": f"admin_deliv_{order_number}", "title": "🚚 تم التوصيل"}
    ])

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
CHANNEL_INVITE_URL = "https://whatsapp.com/channel/0029VaqFTglLikgDDe0D5E2D"
ORDER_THANK_YOU_MESSAGE = (
    "🎉 شكراً جزيلاً لطلبكِ وثقتكِ بنا يا غالية! 💛\n\n"
    "✅ تم استلام طلبك بنجاح، وسنبدأ بتجهيزه قريباً 📦\n"
    "سنظل على تواصل معكِ حتى يصلكِ طلبك بأمان 🚚✨\n\n"
    "📲 أرسلي رابط قناتنا لمن تحبين، لتصلهن أحدث المنتجات والعروض 🛍️💫\n"
    f"🔗 {CHANNEL_INVITE_URL}"
)

def send_order_thank_you(to):
    """إرسال رسالة الشكر ورابط القناة مرة واحدة بعد تسجيل الطلب."""
    return send_message(to, ORDER_THANK_YOU_MESSAGE)

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
        {"id": "order_details", "title": "📋 تفاصيل آخر طلب"},
        {"id": "cancel_order_request", "title": "❌ إلغاء آخر طلب"},
    ])


ORDER_INQUIRY_KEYWORDS = [
    "طلباتي", "طلباتي وين", "طلباتي فين", "الطلبات حقي", "الطلبات حقي وين",
    "الطلب حقي", "طلبي", "طلبي وين", "طلبي فين", "طلبي حقي", "طلبياتي",
    "الطلبية", "الطلبيه", "طلبيتي", "طلباتى", "طلباتي السابقه", "طلباتي السابقة",
    "الطلبات السابقه", "الطلبات السابقة", "طلب سابق", "طلبات سابقه", "طلبات سابقة",
    "ايش طلبت", "ايش طلبت منك", "ايش طلبت منكم", "ايش طلبتوا", "ماذا طلبت",
    "وش طلبت", "وش طلبت منكم", "ايش رفعت", "ايش رفعت لك", "ايش رفعت لكم",
    "ايش رفعت عندكم", "ايش رفعت لسه", "ايش سجلت", "ايش سجلت عندكم",
    "الطلب اللي رفعته", "الطلب الي رفعته", "الطلب الذي رفعته", "الطلب المرفوع",
    "وين طلبي", "وين الطلب", "وين الطلب حقي", "وين طلبي حقي", "وين الطلبات",
    "فين طلبي", "فين الطلب", "فين الطلب حقي", "فين الطلبات", "اين طلبي",
    "اين الطلب", "أين طلبي", "أين الطلب", "وين وصلت طلباتي", "وين وصل طلبي",
    "كيف طلبي", "كيف الطلب", "كيف طلباتي", "ايش صار في طلبي", "ايش صار بالطلب",
    "حالة طلبي", "حاله طلبي", "حالة الطلب", "حاله الطلب", "ايش حالة طلبي",
    "ايش حاله طلبي", "ايش حالة الطلب", "وضع طلبي", "وضع الطلب", "ايش وضع طلبي",
    "ايش وضع الطلب", "اخر تحديث للطلب", "آخر تحديث للطلب", "تحديث الطلب",
    "تحديث حالة الطلب", "حدثوا الطلب", "حدث الطلب", "متابعة الطلب", "متابعه الطلب",
    "متابعة طلبي", "متابعه طلبي", "تتبع الطلب", "تتبع طلبي", "اتتبع طلبي",
    "اتابع طلبي", "تابع طلبي", "استفسار عن طلبي", "استفسار عن الطلب",
    "استعلام عن الطلب", "استعلام عن طلبي", "شوف طلبي", "شوفوا طلبي", "شيك طلبي",
    "شيكوا على طلبي", "راجع طلبي", "راجعي طلبي", "وريني طلباتي", "وريني طلبي",
    "عرض طلباتي", "عرض طلبي", "اعرض طلباتي", "ارسل طلباتي", "ارسلوا طلباتي",
    "افتح طلباتي", "اريد طلباتي", "أريد طلباتي", "ابغى طلباتي", "اشتي طلباتي",
    "كم طلب عندي", "كم طلباتي", "رقم طلبي", "رقم الطلب", "رقم الطلب حقي",
    "هل سجلت طلبي", "هل سجلتوا طلبي", "هل تم تسجيل طلبي", "سجلتوا طلبي",
    "تأكيد الطلب", "تاكيد الطلب", "الطلب مؤكد", "هل الطلب مؤكد", "متى يوصل طلبي",
    "متى يوصل الطلب", "متى الطلب يوصل", "متى توصل الطلبية", "وصل طلبي",
    "وصل الطلب", "الشحنة", "الشحنه", "فين الشحنة", "وين الشحنة", "تتبع الشحنه",
]
_NORMALIZED_ORDER_INQUIRY_KEYWORDS = {
    normalize_text(keyword) for keyword in ORDER_INQUIRY_KEYWORDS
}


def is_order_inquiry(msg_normalized):
    """تمييز سؤال العميل عن طلباته قبل تشغيل مطابقة المنتجات أو الرد العام."""
    if not msg_normalized:
        return False
    if msg_normalized in _NORMALIZED_ORDER_INQUIRY_KEYWORDS:
        return True
    return any(
        len(keyword) >= 4 and keyword in msg_normalized
        for keyword in _NORMALIZED_ORDER_INQUIRY_KEYWORDS
    )


ORDER_DETAIL_KEYWORDS = [
    "تفاصيل طلبي", "تفاصيل الطلب", "ايش داخل طلبي", "ايش داخل الطلب",
    "ايش في طلبي", "ايش في الطلب", "محتويات طلبي", "محتويات الطلب",
    "منتجات طلبي", "المنتجات في طلبي", "ايش المنتجات في الطلب", "كم قطعة في الطلب",
    "كم قطعه في الطلب", "اجمالي طلبي", "اجمالي الطلب", "قيمة طلبي", "قيمه الطلب",
    "ايش طلبت", "ايش طلبت منك", "ايش طلبت منكم", "ماذا طلبت", "وش طلبت",
    "ايش رفعت", "ايش رفعت لسه", "ايش سجلت", "الطلب اللي رفعته", "الطلب الي رفعته",
]
PAYMENT_STATUS_KEYWORDS = [
    "هل وصل التحويل", "وصل التحويل", "تأكد التحويل", "تاكد التحويل",
    "هل تأكد الدفع", "هل تاكد الدفع", "حالة الدفع", "حاله الدفع",
    "اشعار التحويل", "إشعار التحويل", "ارسلت التحويل", "أرسلت التحويل",
    "ارسلت صورة التحويل", "أرسلت صورة التحويل", "هل استلمتوا الحوالة",
    "الحوالة وصلت", "الحواله وصلت", "خلصت الدفع", "تم الدفع", "الدفع تم",
    "متى يتأكد الدفع", "متى يتاكد الدفع", "راجعوا التحويل", "راجعوا الحوالة",
]
CANCEL_ORDER_KEYWORDS = [
    "الغي طلبي", "الغاء الطلب", "الغاء طلبي", "ألغي الطلب", "أريد إلغاء الطلب",
    "ما عاد اشتي الطلب", "ما عاد اريد الطلب", "شيلوا طلبي", "اشطبوا الطلب",
    "لا عاد اريد الطلب", "الغوا الطلب", "الغو الطلب", "الغوا الطلب حقي",
    "الغوا الطلبية", "اشطب طلبي", "شطب الطلب", "الغوا الاوردر", "الغوا الاورد", "الغوا طلبي",
]
ADDRESS_UPDATE_KEYWORDS = [
    "غير العنوان", "غيروا العنوان", "تغيير العنوان", "تعديل العنوان",
    "اريد اغير العنوان", "أريد أغير العنوان", "غير نقطة التوصيل",
    "غيروا نقطة التوصيل", "وصلوه مكان ثاني", "العنوان غلط", "كتبت العنوان غلط",
    "مكان التوصيل غلط", "غيروا مكان التوصيل", "غير مكان الاستلام", "نقطة الاستلام غلط",
]
ORDER_EDIT_KEYWORDS = [
    "أعدل طلبي", "اعدل طلبي", "تعديل الطلب", "غير الطلب", "غيروا الطلب",
    "اضيف للطلب", "أضيف للطلب", "احذف من الطلب", "أحذف من الطلب",
    "غير الكمية في الطلب", "زودوا المنتج في الطلب", "نقصوا المنتج من الطلب",
    "اريد اضافة منتج للطلب", "أريد إضافة منتج للطلب", "ابغى ازيد الطلب",
    "اشتي ازيد الطلب", "نسيت منتج", "نسيت أضيف منتج",
]
CUSTOMER_COMPLAINT_KEYWORDS = [
    "الطلب ناقص", "طلبي ناقص", "وصلني منتج غلط", "المنتج غلط",
    "الطلب ما وصل", "طلبي ما وصل", "الطلب متأخر", "طلبي متأخر",
    "في مشكلة بالطلب", "في مشكله بالطلب", "شكوى على الطلب", "اشتكاء على الطلب",
    "الطلب ناقص منه", "وصل ناقص", "ما استلمت الطلب", "ما استلمت المنتج",
    "ابي ارجع المنتج", "ابغى ارجع المنتج", "اشتي ارجع المنتج", "استبدال المنتج",
    "استرجاع الطلب", "استرجاع المبلغ", "رجعوا فلوسي", "ارجعوا المبلغ",
]
_NORMALIZED_ORDER_DETAIL_KEYWORDS = {normalize_text(k) for k in ORDER_DETAIL_KEYWORDS}
_NORMALIZED_PAYMENT_STATUS_KEYWORDS = {normalize_text(k) for k in PAYMENT_STATUS_KEYWORDS}
_NORMALIZED_CANCEL_ORDER_KEYWORDS = {normalize_text(k) for k in CANCEL_ORDER_KEYWORDS}
_NORMALIZED_ADDRESS_UPDATE_KEYWORDS = {normalize_text(k) for k in ADDRESS_UPDATE_KEYWORDS}
_NORMALIZED_ORDER_EDIT_KEYWORDS = {normalize_text(k) for k in ORDER_EDIT_KEYWORDS}
_NORMALIZED_CUSTOMER_COMPLAINT_KEYWORDS = {normalize_text(k) for k in CUSTOMER_COMPLAINT_KEYWORDS}


def _matches_keyword_set(msg_normalized, keywords):
    """مطابقة عبارة كاملة أو جزء واضح منها مع تجاهل الهمزات والترقيم."""
    if not msg_normalized:
        return False
    return msg_normalized in keywords or any(
        len(keyword) >= 5 and keyword in msg_normalized for keyword in keywords
    )


def is_order_detail_inquiry(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_ORDER_DETAIL_KEYWORDS)


def is_payment_status_inquiry(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_PAYMENT_STATUS_KEYWORDS)


def is_cancel_order_request(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_CANCEL_ORDER_KEYWORDS)


def is_address_update_request(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_ADDRESS_UPDATE_KEYWORDS)


def is_order_edit_request(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_ORDER_EDIT_KEYWORDS)


def is_customer_complaint(msg_normalized):
    return _matches_keyword_set(msg_normalized, _NORMALIZED_CUSTOMER_COMPLAINT_KEYWORDS)


def extract_order_number(value):
    """استخراج رقم الطلب عند إرساله مع ORD أو كلمة طلب، دون اعتبار أي رقم عشوائي طلباً."""
    text = str(value or "").strip()
    if not re.search(r"ord|طلب|رقم|حاله|حالة|تتبع|تفاصيل|وضع", text, re.IGNORECASE):
        return ""
    match = re.search(r"(?:ord\s*[-_]?\s*|طلب\s*(?:رقم)?\s*)?(\d{3,8})", text, re.IGNORECASE)
    return normalize_order_number(match.group(1)) if match else ""


def latest_customer_order(phone_number):
    orders = get_customer_orders(phone_number, limit=1)
    return orders[0] if orders else None


def customer_order_by_number(phone_number, order_number):
    if not order_number:
        return None
    order = get_order(order_number)
    if order and order.get("phone_number") == phone_number:
        return order
    return None


def format_customer_order_details(order):
    """تنسيق تفاصيل طلب العميل دون كشف بيانات إدارية غير لازمة."""
    lines = [
        f"📦 *تفاصيل طلبك: {order.get('order_number', 'غير محدد')}*",
        f"📊 الحالة: *{order.get('order_status') or 'جديد'}*",
        f"💳 الدفع: {order.get('payment_method') or 'غير محدد'}",
        f"🕐 التاريخ: {order.get('created_at') or 'غير محدد'}",
        "",
        "🛍️ *المنتجات:*",
    ]
    for item in order.get("products_data", []) or []:
        quantity = int(item.get("quantity", item.get("qty", 1)) or 1)
        price = float(item.get("price", 0) or 0)
        lines.append(f"• {item.get('name', 'منتج')} × {quantity} = {int(price * quantity)} ريال")
    lines.append(f"\n💰 *الإجمالي: {int(float(order.get('total_price', 0) or 0))} ريال*")
    if order.get("payment_proof_url"):
        lines.append("📸 تم استلام صورة إشعار التحويل مع الطلب.")
    return "\n".join(lines)


def send_customer_order_details(to, order=None):
    order = order or latest_customer_order(to)
    if not order:
        send_message(to, "📦 لا توجد طلبات مسجلة على رقمك حالياً.")
        return
    send_message(to, format_customer_order_details(order))
    send_buttons(to, "اختاري الإجراء المناسب:", [
        {"id": "menu_orders", "title": "🔄 تحديث الطلبات"},
        {"id": "order_payment_status", "title": "💳 حالة الدفع"},
        {"id": "cancel_order_request", "title": "❌ إلغاء الطلب"},
    ])


def send_customer_payment_status(to):
    order = latest_customer_order(to)
    if not order:
        send_message(to, "💳 لا يوجد طلب مسجل حتى الآن. يمكنك إضافة منتج ثم إكمال الطلب.")
        return
    proof_status = "✅ تم إرفاق إشعار التحويل" if order.get("payment_proof_url") else "لم يتم إرفاق إشعار تحويل"
    send_message(
        to,
        f"💳 *حالة الدفع لطلبك {order.get('order_number')}*\n\n"
        f"طريقة الدفع: {order.get('payment_method') or 'غير محددة'}\n"
        f"حالة الطلب: *{order.get('order_status') or 'جديد'}*\n"
        f"إشعار التحويل: {proof_status}",
    )


def request_order_cancellation(to, order_number=""):
    order = customer_order_by_number(to, order_number) if order_number else latest_customer_order(to)
    if not order:
        send_message(to, "📦 لا توجد طلبات مسجلة يمكن إلغاؤها حالياً.")
        return
    if order.get("order_status") not in {"جديد", "بانتظار مراجعة الدفع"}:
        send_message(to, "⚠️ لا يمكن إلغاء الطلب بعد بدء تجهيزه أو شحنه. سأتواصل مع الإدارة لمساعدتكِ.")
        send_message(OWNER_NUMBER, f"📩 طلب إلغاء غير آلي من العميل {to}\nالطلب: {order.get('order_number')}\nالحالة: {order.get('order_status')}")
        return
    session_data = user_sessions.get(to, {}) if isinstance(user_sessions.get(to, {}), dict) else {}
    session_data["cancel_order_number"] = order.get("order_number")
    user_sessions[to] = session_data
    user_states[to] = "awaiting_order_cancellation"
    send_buttons(to, f"هل تريدين إلغاء الطلب {order.get('order_number')}؟", [
        {"id": "confirm_cancel_order", "title": "✅ نعم، إلغاء الطلب"},
        {"id": "keep_order", "title": "↩️ إبقاء الطلب"},
    ])


def request_address_update(to):
    order = latest_customer_order(to)
    if not order:
        send_message(to, "📍 لا يوجد طلب مسجل حالياً لتعديل عنوانه. يمكنك إكمال طلب جديد أولاً.")
        return
    user_states[to] = "awaiting_address_update"
    session_data = user_sessions.get(to, {}) if isinstance(user_sessions.get(to, {}), dict) else {}
    session_data["address_order_number"] = order.get("order_number")
    user_sessions[to] = session_data
    send_message(to, "📍 أرسلي العنوان الجديد أو أقرب نقطة للتوصيل، وسأرفعه للإدارة للتحديث 😊")


def request_order_edit(to):
    order = latest_customer_order(to)
    if not order:
        send_message(to, "📦 لا يوجد طلب مسجل حالياً لتعديله.")
        return
    user_states[to] = "awaiting_order_edit_request"
    session_data = user_sessions.get(to, {}) if isinstance(user_sessions.get(to, {}), dict) else {}
    session_data["edit_order_number"] = order.get("order_number")
    user_sessions[to] = session_data
    send_message(to, "✏️ اكتبي التعديل المطلوب على الطلب، مثل: إضافة منتج أو حذف منتج أو تغيير الكمية، وسأرسله للإدارة 😊")


def request_customer_complaint(to):
    order = latest_customer_order(to)
    if not order:
        user_states[to] = "awaiting_general_complaint"
        send_message(to, "🙏 أرسلي تفاصيل المشكلة وسأرفعها للإدارة مباشرة، حتى لو لم يوجد طلب مسجل.")
    else:
        user_states[to] = "awaiting_customer_complaint"
        session_data = user_sessions.get(to, {}) if isinstance(user_sessions.get(to, {}), dict) else {}
        session_data["complaint_order_number"] = order.get("order_number")
        user_sessions[to] = session_data
        send_message(to, f"🙏 أرسلي تفاصيل المشكلة في الطلب {order.get('order_number')} وسأتابعها مع الإدارة مباشرة.")


def notify_owner_customer_request(sender, request_text, category):
    send_message(
        OWNER_NUMBER,
        f"📩 *طلب متابعة من عميل*\n\n"
        f"👤 الرقم: {sender}\n"
        f"📌 النوع: {category}\n"
        f"💬 الرسالة: {request_text}",
    )

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
        variant_label = f" ({item['variant_name']})" if item.get("variant_name") else ""
        lines.append(f"• {item['name']}{variant_label} × {item['quantity']} = {int(item_total)} ريال")
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


def find_admin_product(product_query):
    """العثور على منتج للإدارة بعد توحيد الهمزات والاختلافات الإملائية."""
    query = normalize_text(product_query)
    if not query:
        return None, []
    products = get_all_products()
    exact = [p for p in products if query == normalize_text(p.get("name", ""))]
    if len(exact) == 1:
        return exact[0], exact
    matches = [
        p for p in products
        if query in normalize_text(p.get("name", ""))
        or normalize_text(p.get("name", "")) in query
    ]
    return (matches[0] if len(matches) == 1 else None), matches


def admin_product_match_error(product_query, matches):
    if not matches:
        return f"❌ لم أجد المنتج: {product_query}\nاكتبي جزءاً أوضح من الاسم بدون همزات أو معها."
    names = "\n".join(f"• {p.get('name', '')}" for p in matches[:8])
    return f"⚠️ وجدت أكثر من منتج مطابق، اكتبي اسماً أطول:\n{names}"


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

    # === التعامل مع الرد المباشر المقتبس (الضغط مطولاً على إشعار العميل ثم الرد) ===
    context_info = message.get("context") or {}
    quoted_id = context_info.get("id", "")
    # بعض إصدارات واتساب تضع النص المقتبس في context.get("text") أو context.get("body")
    quoted_text = str(context_info.get("text", "") or context_info.get("body", "") or "")
    
    print(f"[تشخيص الرد المقتبس] quoted_id={quoted_id}, quoted_text={quoted_text}, msg_body={msg_body}")

    if (quoted_id or quoted_text) and msg_body:
        target_phone = ""
        
        # 1. البحث في النص المقتبس أولاً لأنه مضمون ويحتوي رقم العميل صراحةً (مثل: الرقم: 967712282204)
        if quoted_text:
            phone_match = re.search(r"(?:الرقم\s*[:：]?\s*)?([+]?967\d{9}|[+]?[7]\d{8})", quoted_text)
            if phone_match:
                raw_num = phone_match.group(1) or phone_match.group(0)
                target_phone = re.sub(r"\D", "", raw_num)
                if target_phone.startswith("00"):
                    target_phone = target_phone[2:]

        # 2. إن لم نجد الرقم في النص المقتبس، نبحث عبر wamid في قاعدة البيانات
        if not target_phone and quoted_id:
            try:
                with db_lock:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    row = conn.execute(
                        "SELECT phone_number FROM message_events WHERE whatsapp_message_id = ? LIMIT 1",
                        (quoted_id,)
                    ).fetchone()
                    if row and row["phone_number"]:
                        target_phone = str(row["phone_number"])
            except Exception as e:
                print(f"[تشخيص الرد المقتبس] خطأ قاعدة البيانات عند البحث بـ wamid: {e}")

        print(f"[تشخيص الرد المقتبس] target_phone المستخرج={target_phone}")

        if target_phone:
            reply_text = msg_body.strip()
            if reply_text:
                sent = send_message(target_phone, reply_text)
                print(f"[تشخيص الرد المقتبس] نتيجة send_message للعميل={sent}")
                if sent:
                    send_message(OWNER_NUMBER, f"✅ تم إرسال الرد إلى العميل مباشرة ({target_phone})")
                else:
                    queue_pending_reply(target_phone, reply_text)
                    send_message(OWNER_NUMBER, f"✅ تم حفظ الرد للعميل ({target_phone}) وسيصل عند تواصله.")
                return True
        else:
            # تنبيه الإدارة أن الرقم لم يُستخرج لكي لا تظل صامتة
            send_message(OWNER_NUMBER, "⚠️ لم أتمكن من معرفة رقم العميل من الرسالة المقتبسة. يرجى الرد باستخدام: رد [الرقم] [الرسالة]")
            return True

    # === التعامل مع أزرار الإدارة (تم التجهيز / تم التوصيل) ===
    if msg_body.startswith("admin_prep_") or msg_body.startswith("admin_deliv_"):
        parts = msg_body.split("_")
        if len(parts) >= 3:
            action_type = parts[1] # prep or deliv
            order_number = "_".join(parts[2:])
            order = get_order(order_number)
            if order:
                customer_phone = order.get("phone_number")
                if action_type == "prep":
                    update_order_status(order_number, "جاري التجهيز")
                    send_message(OWNER_NUMBER, f"✅ تم تحديث حالة الطلب {order_number} إلى: *جاري التجهيز*")
                    if customer_phone:
                        send_message(customer_phone, f"📦 *تحديث لطلبك {order_number}*\n\n✅ جاري تجهيز طلبك الآن وسيتم إرساله قريباً بشغف وسعادة 😊")
                elif action_type == "deliv":
                    update_order_status(order_number, "تم التسليم")
                    send_message(OWNER_NUMBER, f"🚚 تم تحديث حالة الطلب {order_number} إلى: *تم التسليم*")
                    if customer_phone:
                        send_message(customer_phone, f"🎉 *تحديث لطلبك {order_number}*\n\n🚚 تم تسليم طلبك بنجاح! شكراً لثقتكِ الغالية بمتجر Titiz 💛✨")
            else:
                send_message(OWNER_NUMBER, f"❌ لم أجد الطلب برقم: {order_number}")
        return True

    # === إضافة منتج جديد من رقم الإدارة بأمر «اضف» (صورة اختيارية + اسم وسعر) ===
    is_image_add = (message.get("type") == "image")
    is_add_command = bool(re.match(r"^\s*(?:اضف|إضافة)\b", msg_body or "", re.IGNORECASE))
    add_match = re.search(r"(?:اسم\s*المنتج|المنتج|اضف|إضافة)\s*[:：]?\s*([^\n,]+)(?:[\n,].*?السعر\s*[:：]?\s*(\d+))?", msg_body or "", re.IGNORECASE) if is_add_command else None
    
    if is_add_command:
        prod_name = ""
        prod_price = 0
        
        if add_match:
            prod_name = add_match.group(1).strip()
            if add_match.group(2):
                try:
                    prod_price = int(add_match.group(2))
                except ValueError:
                    pass
        
        if prod_price == 0:
            price_match = re.search(r"(?:السعر|بـ|سعرة)\s*[:：]?\s*(\d+)", msg_body or "", re.IGNORECASE)
            if price_match:
                try:
                    prod_price = int(price_match.group(1))
                except ValueError:
                    pass
            else:
                nums = re.findall(r"\b\d{2,6}\b", msg_body or "")
                if nums:
                    prod_price = int(nums[-1])

        if not prod_name and msg_body:
            lines = [l.strip() for l in msg_body.split("\n") if l.strip()]
            if lines:
                prod_name = lines[0].replace("اسم المنتج:", "").replace("المنتج:", "").replace("اضف", "").strip()

        # إذا توفرت الصورة أو السعر، نبدأ المعالجة
        if prod_name or prod_price > 0 or is_image_add:
            if not prod_name:
                prod_name = "منتج جديد من الإدارة"
            if prod_price <= 0:
                prod_price = 1000  # سعر افتراضي مؤقت إن لم يُكتب صريحاً لتجنب التوقف

            send_message(OWNER_NUMBER, f"⏳ *جاري إضافة المنتج ({prod_name}) ومعالجة البيانات والصورة...*")

            image_id = message.get("image", {}).get("id", "") if is_image_add else ""
            image_url = ""
            if image_id:
                try:
                    image_url = get_media_url_by_id(image_id) or ""
                except Exception as e:
                    print(f"[إضافة منتج] خطأ جلب الصورة: {e}")

            # طريقة «اضف» السابقة: وصف ثابت واضح وكلمات بحث مشتقة من اسم المنتج فقط.
            # لا يتم استدعاء الذكاء الاصطناعي أو تحليل الصورة في هذا المسار.
            marketing_desc = f"منتج حصري وعالي الجودة من منتجات المائدة والضيافة العصرية. {prod_name} بتصميم أنيق ومميز يضفي لمسة جمالية وفخامة لمنزلك."
            keywords = f"{prod_name}, أواني منزلية, تجهيز مطابخ, تيتيز, إب"
            if "ثلاجة" in prod_name or "شاي" in prod_name:
                keywords += ", حافظات حرارة, دلال قهوة"
            elif "قدر" in prod_name or "طباخة" in prod_name:
                keywords += ", قدور طهي, أدوات مطبخ"

            try:
                import database as db_mod
                db_mod.add_product(
                    name=prod_name,
                    price=prod_price,
                    description=marketing_desc,
                    image_id=image_url,
                    keywords=keywords
                )

                # رسالة التأكيد
                send_message(OWNER_NUMBER, f"✅ *تمت إضافة المنتج بنجاح وتم تحديث الكتالوج!*")

                # إرسال بطاقة المنتج النهائية (صورة إن وجدت + النص التنسيقي الكامل)
                card_text = (
                    f"☕ *{prod_name}*\n\n"
                    f"📝 *الوصف:* {marketing_desc}\n"
                    f"💰 *السعر:* {prod_price} ريال\n"
                    f"🔑 *الكلمات المفتاحية:* {keywords}"
                )

                if image_url:
                    send_image_message(OWNER_NUMBER, image_url, card_text)
                else:
                    send_message(OWNER_NUMBER, card_text)

            except Exception as ex:
                send_message(OWNER_NUMBER, f"❌ حدث خطأ أثناء حفظ المنتج في قاعدة البيانات: {ex}")

            return True

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
                if price_val <= 0:
                    send_message(OWNER_NUMBER, "❌ لا يمكن إضافة المنتج بدون سعر صحيح أكبر من صفر.\nالصيغة: اضف اسم المنتج | السعر | الوصف | الكلمات المفتاحية")
                    return True
                product_id = add_product(product_name, price_val, product_desc, "", 100, keywords_str)
                if not product_id:
                    send_message(OWNER_NUMBER, f"❌ لم تتم إضافة المنتج؛ الاسم موجود مسبقاً أو السعر غير صالح: {product_name}")
                    return True
                saved = sync_products_to_github()
                if saved:
                    send_message(OWNER_NUMBER, f"✅ تم إضافة وحفظ المنتج دائمًا على GitHub:\n📦 {product_name}\n💰 {int(price_val)} ريال\n📝 {product_desc}\n🔑 كلمات: {keywords_str or 'لا يوجد'}\n\nلإضافة صورة: أرسل صورة مع كابشن فيه اسم المنتج")
                    product = get_product(product_id)
                    if product:
                        send_admin_share_card(product)
                else:
                    send_message(OWNER_NUMBER, f"⚠️ تم إضافة المنتج محلياً، لكن *فشل حفظه على GitHub* (تأكد من GITHUB_TOKEN):\n📦 {product_name}\n💰 {int(price_val)} ريال")
            else:
                send_message(OWNER_NUMBER, "❌ الصيغة: اضف [اسم] | [سعر] | [وصف] | [كلمات مفتاحية]")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: اضف [اسم] | [سعر] | [وصف] | [كلمات مفتاحية]")
        return True

    # === تعديل منتج كامل ===
    if msg_normalized.startswith("عدل منتج") or msg_normalized.startswith("عدل المنتج"):
        edit_text = re.sub(r"^\s*عدل\s+(?:ال)?منتج\s*", "", msg_body, count=1).strip()
        parts = [part.strip() for part in edit_text.split("|")]
        if len(parts) >= 4:
            old_name, new_name, price_value, description = parts[:4]
            price_match = re.search(r"\d+(?:\.\d+)?", price_value)
            product, matches = find_admin_product(old_name)
            if not product:
                send_message(OWNER_NUMBER, admin_product_match_error(old_name, matches))
            elif not price_match:
                send_message(OWNER_NUMBER, "❌ السعر يجب أن يكون رقماً، مثال: 1500")
            else:
                new_price = float(price_match.group(0))
                updated = update_product_fields(
                    product["id"], name=new_name, price=new_price, description=description
                )
                if updated == "duplicate":
                    send_message(OWNER_NUMBER, f"❌ الاسم الجديد موجود بالفعل: {new_name}")
                elif updated == "invalid_price":
                    send_message(OWNER_NUMBER, "❌ لا يمكن تعديل المنتج بسعر فارغ أو صفر. أدخل سعراً أكبر من صفر.")
                elif updated:
                    saved = sync_products_to_github(remove_names=[product["name"]])
                    status = "✅ وحُفظ على GitHub" if saved else "⚠️ تم محلياً، لكن تعذّر الحفظ على GitHub"
                    send_message(
                        OWNER_NUMBER,
                        f"✅ تم تعديل المنتج {product['name']} بالكامل\n"
                        f"📦 الاسم الجديد: {new_name}\n💰 السعر: {int(new_price)} ريال\n"
                        f"📝 الوصف: {description}\n{status}",
                    )
            return True
        send_message(
            OWNER_NUMBER,
            "❌ الصيغة الصحيحة:\nعدل منتج | الاسم القديم | الاسم الجديد | السعر | الوصف",
        )
        return True

    # === تعديل الاسم ===
    if msg_normalized.startswith("عدل اسم "):
        edit_text = re.sub(r"^\s*عدل\s+اسم\s*", "", msg_body, count=1).strip()
        parts = [part.strip() for part in edit_text.split("|", 1)]
        if len(parts) == 2 and all(parts):
            old_name, new_name = parts
            product, matches = find_admin_product(old_name)
            if not product:
                send_message(OWNER_NUMBER, admin_product_match_error(old_name, matches))
            else:
                updated = update_product_fields(product["id"], name=new_name)
                if updated == "duplicate":
                    send_message(OWNER_NUMBER, f"❌ الاسم الجديد موجود بالفعل: {new_name}")
                else:
                    saved = sync_products_to_github(remove_names=[product["name"]])
                    status = "وحُفظ على GitHub ✅" if saved else "تم محلياً فقط ⚠️"
                    send_message(OWNER_NUMBER, f"✅ تم تغيير اسم المنتج إلى: {new_name}\n{status}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: عدل اسم | الاسم القديم | الاسم الجديد")
        return True

    # === تعديل الوصف ===
    if msg_normalized.startswith("عدل وصف "):
        edit_text = re.sub(r"^\s*عدل\s+وصف\s*", "", msg_body, count=1).strip()
        parts = [part.strip() for part in edit_text.split("|", 1)]
        if len(parts) == 2 and all(parts):
            product_name, description = parts
            product, matches = find_admin_product(product_name)
            if not product:
                send_message(OWNER_NUMBER, admin_product_match_error(product_name, matches))
            else:
                updated = update_product_fields(product["id"], description=description)
                if updated:
                    saved = sync_products_to_github()
                    status = "وحُفظ على GitHub ✅" if saved else "تم محلياً فقط ⚠️"
                    send_message(OWNER_NUMBER, f"✅ تم تعديل وصف {product['name']}\n{status}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: عدل وصف | اسم المنتج | الوصف الجديد")
        return True

    # === تعديل سعر ===
    if msg_normalized.startswith("عدل سعر "):
        raw_edit = re.sub(r"^\s*عدل\s+سعر\s*", "", msg_body, count=1).strip()
        if "|" in raw_edit:
            product_name, price_value = [part.strip() for part in raw_edit.split("|", 1)]
            text = f"{product_name} {price_value}"
        else:
            text = raw_edit
            product_name = ""
            price_value = ""
        price_match = re.search(r'\b(\d+)\b', text)
        if price_match:
            product_name = product_name or text[:price_match.start()].strip()
            new_price = float(price_match.group(1))
            product, matches = find_admin_product(product_name)
            if not product:
                send_message(OWNER_NUMBER, admin_product_match_error(product_name, matches))
            else:
                price_update = update_product_fields(product["id"], price=new_price)
                if price_update == "invalid_price":
                    send_message(OWNER_NUMBER, "❌ لا يمكن تعديل السعر إلى صفر أو قيمة فارغة. أدخل سعراً أكبر من صفر.")
                elif price_update:
                    saved = sync_products_to_github()
                    status = "وحُفظ على GitHub ✅" if saved else "تم محلياً فقط ⚠️"
                    send_message(OWNER_NUMBER, f"✅ تم تعديل سعر {product['name']} إلى {int(new_price)} ريال\n{status}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: عدل سعر | اسم المنتج | السعر الجديد")
        return True

    # === حذف منتج ===
    if msg_normalized.startswith("حذف ") and not msg_normalized.startswith("حذف رد"):
        product_name = msg_body[4:].strip()
        product, matches = find_admin_product(product_name)
        if not product:
            send_message(OWNER_NUMBER, admin_product_match_error(product_name, matches))
            return True
        from database import db_lock, DB_PATH
        import sqlite3 as _sqlite3
        with db_lock:
            conn = _sqlite3.connect(DB_PATH)
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product["id"],))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        if deleted:
            sync_products_to_github(remove_names=[product["name"]])
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
                updated = update_order_status(order_num, new_status)
                order = get_order(order_num)
                if not updated or not order:
                    send_message(OWNER_NUMBER, f"❌ لم أجد الطلب أو تعذر تحديثه: {order_num}")
                else:
                    if order.get("phone_number"):
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
        help_text += "• عدل منتج | القديم | الجديد | السعر | الوصف\n"
        help_text += "• عدل اسم | القديم | الجديد\n"
        help_text += "• عدل وصف | اسم المنتج | الوصف\n"
        help_text += "• عدل سعر | اسم المنتج | السعر\n"
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
                    created_id = add_product(caption, 0, "", media_id, 100, "")
                    if created_id:
                        send_message(OWNER_NUMBER, f"✅ تم حفظ الصورة كمنتج جديد: {caption}")
                    else:
                        send_message(OWNER_NUMBER, f"❌ لم تُحفظ الصورة كمنتج جديد لأن السعر غير محدد. أرسل السعر أولاً ثم أرسل الصورة مع كابشن: {caption}")
                else:
                    send_message(OWNER_NUMBER, f"✅ تم إضافة صورة للمنتج: {caption}")
                conn.commit()
                conn.close()
            sync_products_to_github()
            product, _ = find_admin_product(caption)
            if product:
                send_admin_share_card(product, image_id=media_id)
        elif media_id and not caption:
            send_message(OWNER_NUMBER, "❌ أرسل الصورة مع كابشن فيه اسم المنتج")
        return True

    return False


# ╔══════════════════════════════════════════════════════════════╗
# ║                 معالجة رسائل العملاء                         ║
# ╚══════════════════════════════════════════════════════════════╝

_last_outbound_customer_reply = {}
_outbound_reply_lock = __import__("threading").Lock()

def handle_customer_message(sender, msg_body, msg_normalized, message):
    """معالجة رسائل العملاء مع حماية صارمة ضد تكرار الرد للرسالة الواحدة"""
    with _outbound_reply_lock:
        now = __import__("time").time()
        reply_key = (str(sender), str(msg_normalized or "").strip())
        last_t = _last_outbound_customer_reply.get(reply_key, 0.0)
        if now - last_t < 4.0:
            print(f"[حماية التكرار] تم تجاهل معالجة رسالة مكررة للعميل {sender} خلال {now - last_t:.2f} ثانية")
            return
        _last_outbound_customer_reply[reply_key] = now
        # تنظيف الذاكرة المؤقتة القديمة
        expired = [k for k, t in _last_outbound_customer_reply.items() if now - t > 15.0]
        for k in expired:
            _last_outbound_customer_reply.pop(k, None)

    restore_customer_session(sender)
    restore_customer_session(sender)
    state = user_states.get(sender, "")
    raw_action = (msg_body or "").strip().lower()

    if state == "awaiting_order_cancellation":
        if msg_normalized in {"نعم", "ايوه", "ايوا", "موافق", "الغيه", "الغاء"}:
            raw_action = "confirm_cancel_order"
        elif msg_normalized in {"لا", "خليه", "ابقى الطلب", "ابقي الطلب", "تراجع"}:
            raw_action = "keep_order"

    # أي رسالة جديدة تعني أن العميل عاد للمحادثة؛ نلغي التذكير السابق.
    if raw_action not in {
        PRODUCT_FOLLOWUP_SATISFIED_ID,
        PRODUCT_FOLLOWUP_UNSATISFIED_ID,
    }:
        cancel_customer_followup(sender)

    # بعض أجهزة واتساب تعيد عنوان الزر الظاهر مع الإيموجي بدلاً من المعرّف.
    # نحول العنوان المكتوب أو عنوان الزر إلى نفس المعرّف قبل أن يصل للفهم العام.
    button_text_aliases = {
        "التفاصيل": "details",
        "تفاصيل": "details",
        "اضافة للسلة": "add_to_cart",
        "اضافه للسلة": "add_to_cart",
        "اضف للسلة": "add_to_cart",
        "اضف هذا الحجم": "add_matched_variant",
        "اضافة هذا الحجم": "add_matched_variant",
        "عرض السلة": "menu_cart",
        "السلة": "menu_cart",
        "اكمال الطلب": "checkout",
        "اكمل الطلب": "checkout",
        "تفريغ السلة": "clear_cart",
        "متابعة التسوق": "shopping_assistant",
        "المنتجات": "browse_products",
        "طلباتي": "menu_orders",
        "العروض": "menu_offers",
        "التواصل مع المندوبة": "menu_contact",
        "راضي": PRODUCT_FOLLOWUP_SATISFIED_ID,
        "غير راضي": PRODUCT_FOLLOWUP_UNSATISFIED_ID,
    }
    text_button_action = button_text_aliases.get(msg_normalized)
    session_context = user_sessions.get(sender, {})
    session_context = session_context if isinstance(session_context, dict) else {}
    context_product = session_context.get("last_product")
    context_product = canonicalize_product(context_product) if isinstance(context_product, dict) else None
    if not context_product:
        context_product = get_variant_context_product(sender)

    if text_button_action == "details":
        if context_product:
            raw_action = f"det_{context_product['id']}"
        else:
            send_message(sender, "📋 أرسلي اسم المنتج أو افتحي بطاقته أولاً لعرض التفاصيل.")
            return
    elif text_button_action == "add_to_cart":
        if context_product:
            raw_action = (
                f"variants_{context_product['id']}"
                if product_variants(context_product)
                else f"add_{context_product['id']}"
            )
        else:
            send_message(sender, "🛒 افتحي بطاقة المنتج أو اكتبي اسمه أولاً حتى أضيفه للسلة.")
            return
    elif text_button_action == "add_matched_variant":
        variant_index = session_context.get("matched_variant_index")
        if context_product and isinstance(variant_index, int):
            raw_action = f"variant_{context_product['id']}_{variant_index}"
        elif context_product:
            raw_action = f"variants_{context_product['id']}"
        else:
            send_message(sender, "📏 افتحي بطاقة المنتج أو اختاري الحجم أولاً.")
            return
    elif text_button_action:
        raw_action = text_button_action

    if raw_action == PRODUCT_FOLLOWUP_SATISFIED_ID:
        send_message(sender, PRODUCT_FOLLOWUP_SATISFIED_MESSAGE)
        return

    if raw_action == PRODUCT_FOLLOWUP_UNSATISFIED_ID:
        send_message(sender, PRODUCT_FOLLOWUP_UNSATISFIED_MESSAGE)
        return

    if raw_action == PRODUCT_FOLLOWUP_CONTINUE_ID:
        send_message(sender, "تمام يا غالية 😊 اكتبي اسم المنتج أو سؤالك وسأكمل معكِ من حيث توقفنا.")
        return

    if raw_action == PRODUCT_FOLLOWUP_STOP_ID:
        send_message(sender, PRODUCT_FOLLOWUP_UNSATISFIED_MESSAGE)
        return

    # بعض نسخ WhatsApp تعيد عنوان الزر بدلاً من id؛ افتحي آخر قائمة أحجام محفوظة.
    variant_action_labels = {"اختيار الحجم", "اختيار الحجم والسعر", "اختيار المقاس"}
    # قد يعيد واتساب عنوان الزر كاملاً مثل «📏 اختيار الحجم»؛
    # النص المطبّع يزيل الإيموجي ويحافظ على مسار الأحجام بدلاً من المرور للمساعدة العامة.
    if raw_action in variant_action_labels or msg_normalized in variant_action_labels:
        product = get_variant_context_product(sender)
        if product and any(parse_product_price(v.get("price")) is not None for v in product_variants(product)):
            send_variant_list(sender, product)
        else:
            send_message(sender, "⚠️ افتحي بطاقة المنتج مرة أخرى ثم اضغطي «اختيار الحجم» لعرض الخيارات.")
        return

    # اختيار منتج من قائمة نتائج البحث المتعددة. لا نستخدم أزرار الكاروسيل
    # لأن القائمة الأصلية تعيد list_reply ثابتاً إلى هذا المسار.
    if raw_action.startswith("product_"):
        try:
            product_id = int(raw_action.split("_", 1)[1])
        except (ValueError, IndexError):
            product_id = None
        allowed_ids = session_context.get("matching_product_ids", [])
        allowed_ids = {int(item) for item in allowed_ids if str(item).isdigit()}
        product = get_product(product_id) if product_id and (not allowed_ids or product_id in allowed_ids) else None
        product = canonicalize_product(product) if product else None
        if product:
            send_product_card(sender, product)
        else:
            send_message(sender, "⚠️ انتهت صلاحية هذه النتائج. اكتبي اسم المنتج مرة أخرى وسأعرضه لكِ فوراً.")
        return

    # فتح قائمة أحجام المنتج من بطاقة الكاروسيل.
    if raw_action.startswith("variants_"):
        try:
            product = get_product(int(raw_action.split("_", 1)[1]))
        except (ValueError, IndexError):
            product = None
        product = canonicalize_product(product) if product else None
        if product and any(parse_product_price(v.get("price")) is not None for v in product_variants(product)):
            send_variant_list(sender, product)
        else:
            send_message(sender, "❌ لا توجد خيارات مسعّرة لهذا المنتج حالياً.")
        return

    # اختيار حجم المنتج: نستخدم النص الخام لأن normalize_text يزيل الشرطة السفلية.
    if raw_action.startswith("variant_"):
        try:
            _, product_id_text, variant_index_text = raw_action.split("_", 2)
            product = get_product(int(product_id_text))
            product = canonicalize_product(product) if product else None
            variant_index = int(variant_index_text)
            variants = product_variants(product or {})
            selected = variants[variant_index]
        except (ValueError, IndexError, TypeError, AttributeError):
            product = None
            selected = None
        if product and selected:
            variant_name = str(selected.get("name") or selected.get("label") or "الخيار")
            variant_price = parse_product_price(selected.get("price"))
            if variant_price is None:
                send_message(sender, "⚠️ لا يمكن إضافة هذا الخيار لأن سعره غير محدد حالياً.")
                return
            if not add_to_cart(sender, product["id"], 1, variant_name, variant_price):
                send_message(sender, "⚠️ لا يمكن إضافة هذا الخيار لأن سعره غير صالح حالياً.")
                return
            send_message(
                sender,
                f"✅ تم إضافة *{product['name']}*\n"
                f"📏 الحجم: {variant_name}\n"
                f"💰 السعر: {variant_price} ريال إلى السلة",
            )
            send_buttons(sender, "ماذا تريدين الآن؟", [
                {"id": "menu_cart", "title": "🛒 عرض السلة"},
                {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
            ])
        else:
            send_message(sender, "❌ لم أتمكن من العثور على هذا الخيار، أرسلي اسم المنتج مرة أخرى.")
        return

    # أزرار المنتج: نستخدم النص الخام لأن normalize_text يزيل الشرطة السفلية.
    if raw_action.startswith("add_"):
        try:
            product = get_product(int(raw_action.split("_", 1)[1]))
        except (ValueError, IndexError):
            product = None
        if product:
            if add_to_cart(sender, product["id"], 1):
                send_message(sender, f"✅ تم إضافة *{product['name']}* إلى السلة")
                send_buttons(sender, "ماذا تريدين الآن؟", [
                    {"id": "menu_cart", "title": "🛒 عرض السلة"},
                    {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
                ])
            else:
                send_message(sender, "⚠️ لا يمكن إضافة المنتج لأن سعره غير محدد حالياً.")
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
                {"id": f"variants_{product['id']}", "title": "📏 اختيار الحجم"} if product_variants(product) else {"id": f"add_{product['id']}", "title": "🛒 إضافة للسلة"},
                {"id": "menu_cart", "title": "🛍️ عرض السلة"},
            ])
            schedule_product_followup(sender, product.get("name", ""))
        else:
            send_message(sender, "❌ تفاصيل المنتج غير متاحة حالياً.")
        return

    if raw_action == "order_details":
        send_customer_order_details(sender)
        return

    if raw_action == "order_payment_status":
        send_customer_payment_status(sender)
        return

    if raw_action == "cancel_order_request":
        request_order_cancellation(sender)
        return

    if raw_action == "update_address_request":
        request_address_update(sender)
        return

    if raw_action == "edit_order_request":
        request_order_edit(sender)
        return

    if raw_action == "report_order_issue":
        request_customer_complaint(sender)
        return

    if raw_action == "confirm_cancel_order":
        session_data = user_sessions.get(sender, {}) if isinstance(user_sessions.get(sender, {}), dict) else {}
        order_number = session_data.get("cancel_order_number", "")
        order = customer_order_by_number(sender, order_number)
        if not order:
            send_message(sender, "❌ لم أجد الطلب المطلوب إلغاؤه. أرسلي «طلباتي» للتحديث.")
        elif order.get("order_status") not in {"جديد", "بانتظار مراجعة الدفع"}:
            send_message(sender, "⚠️ بدأ تجهيز هذا الطلب أو شحنه، لذلك لا يمكن إلغاؤه آلياً.")
        elif update_order_status(order_number, "ملغي"):
            send_message(sender, f"✅ تم إلغاء الطلب {order_number} بناءً على طلبكِ.")
            notify_owner_customer_request(sender, f"إلغاء الطلب {order_number}", "إلغاء طلب")
        else:
            send_message(sender, "⚠️ تعذر إلغاء الطلب حالياً، وسأبلغ الإدارة لمراجعته.")
        user_states.pop(sender, None)
        user_sessions.pop(sender, None)
        return

    if raw_action == "keep_order":
        user_states.pop(sender, None)
        session_data = user_sessions.get(sender, {})
        if isinstance(session_data, dict):
            session_data.pop("cancel_order_number", None)
            user_sessions[sender] = session_data
        send_message(sender, "✅ تم إبقاء الطلب كما هو، وسنواصل تجهيزه لكِ بإذن الله.")
        return

    if raw_action == "menu_cart":
        send_cart_view(sender)
        return

    if raw_action == "shopping_assistant":
        send_product_request_menu(sender)
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

    if state == "awaiting_address_update":
        new_address = msg_body.strip()
        if len(new_address) < 3:
            send_message(sender, "📍 أرسلي اسم المنطقة أو أقرب نقطة بشكل أوضح من فضلكِ.")
            return
        customer = get_customer(sender) or {}
        add_customer(sender, customer.get("name"), new_address)
        sync_customers_to_github()
        session_data = user_sessions.get(sender, {})
        if isinstance(session_data, dict):
            session_data.pop("address_order_number", None)
            user_sessions[sender] = session_data
        user_states.pop(sender, None)
        send_message(sender, f"✅ تم حفظ عنوان التوصيل الجديد:\n📍 {new_address}\nوسأبلغ الإدارة بالتحديث الآن.")
        notify_owner_customer_request(sender, f"العنوان الجديد: {new_address}", "تغيير عنوان التوصيل")
        return

    if state == "awaiting_order_edit_request":
        edit_request = msg_body.strip()
        if len(edit_request) < 3:
            send_message(sender, "✏️ اكتبي التعديل المطلوب بالتفصيل، مثل: إضافة منتج أو تغيير الكمية.")
            return
        session_data = user_sessions.get(sender, {})
        order_number = session_data.get("edit_order_number", "") if isinstance(session_data, dict) else ""
        notify_owner_customer_request(sender, f"الطلب {order_number}: {edit_request}", "تعديل طلب")
        user_states.pop(sender, None)
        if isinstance(session_data, dict):
            session_data.pop("edit_order_number", None)
            user_sessions[sender] = session_data
        send_message(sender, "✅ تم استلام طلب التعديل ورفعه للإدارة، وسنرد عليكِ بعد المراجعة.")
        return

    if state == "awaiting_customer_complaint":
        complaint = msg_body.strip()
        if len(complaint) < 3:
            send_message(sender, "🙏 اكتبي تفاصيل المشكلة حتى نساعدكِ بسرعة.")
            return
        session_data = user_sessions.get(sender, {})
        order_number = session_data.get("complaint_order_number", "") if isinstance(session_data, dict) else ""
        notify_owner_customer_request(sender, f"الطلب {order_number}: {complaint}", "شكوى أو مشكلة في طلب")
        user_states.pop(sender, None)
        if isinstance(session_data, dict):
            session_data.pop("complaint_order_number", None)
            user_sessions[sender] = session_data
        send_message(sender, "🙏 وصلتنا ملاحظتك، وتم رفعها للإدارة لمتابعتها معكِ.")
        return

    if state == "awaiting_general_complaint":
        complaint = msg_body.strip()
        if len(complaint) < 3:
            send_message(sender, "🙏 اكتبي تفاصيل المشكلة حتى نساعدكِ بسرعة.")
            return
        notify_owner_customer_request(sender, complaint, "شكوى عامة")
        user_states.pop(sender, None)
        send_message(sender, "🙏 وصلتنا ملاحظتك، وتم رفعها للإدارة لمتابعتها معكِ.")
        return

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
                send_order_thank_you(sender)
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
                send_order_thank_you(sender)
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

    # === فهم صورة المنتج خارج مسار إثبات التحويل ===
    if message.get("type") == "image":
        image_id = message.get("image", {}).get("id", "")
        caption = message.get("image", {}).get("caption", "").strip()
        image_result = None
        try:
            image_result = analyze_product_image(sender, message, caption)
        except Exception as exc:
            print(f"[الصورة] تعذر تحليل صورة المنتج: {exc}")
            image_result = None

        # إذا فشل التحليل أو لم يتوفر مفتاح الذكاء الاصطناعي، نحاول مطابقة الكابشن أو اسم المنتج مباشرة
        if (not image_result or image_result.get("kind") == "unknown") and caption:
            text_matches = match_products_from_text(caption, get_all_products())
            if text_matches:
                image_result = {"kind": "product_family", "products": text_matches}

        if image_result and image_result.get("kind") == "product":
            matched_product = image_result["product"]
            variant_match = image_result.get("variant_match")
            if variant_match:
                send_matched_product_variant_card(sender, matched_product, variant_match)
                return
            related_products = products_related_to_image(matched_product, get_all_products())
            if len(related_products) >= 2:
                send_matching_products_carousel(
                    sender,
                    related_products,
                    query_key=f"image_{matched_product.get('id', '')}",
                )
            else:
                send_product_card(sender, matched_product)
            return
        if image_result and image_result.get("kind") == "product_family":
            family_products = image_result.get("products") or []
            if len(family_products) >= 2:
                send_matching_products_carousel(
                    sender,
                    family_products,
                    query_key=f"caption_{normalize_text(caption)}",
                )
            elif family_products:
                send_product_card(sender, family_products[0])
            return
        if image_result and image_result.get("kind") == "payment_proof":
            send_message(sender, image_result["reply"])
            return

        # أي حالة أخرى غير مطابقة صريحة تعامل كمنتج غير متوفر وتُرسل للإدارة مع الرد الفوري للعميل
        notify_owner_unavailable_product(
            sender,
            caption or (image_result.get("reply") if image_result else "صورة منتج غير مطابقة للكتالوج"),
            source="image",
            image_id=image_id,
        )
        send_unavailable_image_response(sender)
        return

    if state == "product_context":
        context = user_sessions.get(sender, {})
        last_product = context.get("last_product") if isinstance(context, dict) else None
        if last_product:
            add_actions = {
                normalize_text(action)
                for action in [
                    "add", "إضافة", "اضافه", "أضف", "اضف", "ضيف", "ضف",
                    "حط", "حطه", "حطيه", "طلب", "شراء",
                ]
            }
            if msg_normalized in add_actions or is_product_purchase_request(msg_normalized):
                valid_variants = [
                    variant for variant in product_variants(last_product)
                    if parse_product_price(variant.get("price")) is not None
                ]
                if valid_variants:
                    send_message(sender, f"📏 اختاري الحجم أو الخيار المطلوب من *{last_product['name']}* أولاً 😊")
                    send_variant_list(sender, last_product)
                    return
                if add_to_cart(sender, last_product["id"], 1):
                    send_message(sender, f"✅ تم إضافة *{last_product['name']}* إلى السلة")
                    send_buttons(sender, "ماذا تريدين الآن؟", [
                        {"id": "menu_cart", "title": "🛒 عرض السلة"},
                        {"id": "checkout", "title": "✅ إكمال الطلب"},
                        {"id": "shopping_assistant", "title": "🛍️ متابعة التسوق"},
                    ])
                else:
                    send_message(sender, "⚠️ لا يمكن إضافة المنتج لأن سعره غير محدد حالياً.")
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
                    if not add_to_cart(sender, p['id'], 1):
                        send_message(sender, "⚠️ لا يمكن إضافة المنتج لأن سعره غير محدد حالياً.")
                        return
                    price = parse_product_price(p.get("price"))
                    send_message(sender, f"✅ تم إضافة *{p['name']}* للسلة!\n💰 السعر: {int(price)} ريال\n\nاكتبي *السلة* لعرض المشتريات\nأو *اكمل الطلب* لإتمام الشراء 😊")
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
        send_product_request_menu(sender)
        return

    if raw_action == "browse_products" or msg_normalized == "browseproducts":
        send_message(
            sender,
            "بالتأكيد! أنا هنا لمساعدتك في العثور على أي منتج تبحث عنه على **Titiz**\n"
            "يرجى إخباري باسم المنتج أو الفئة التي تهمك، وسأقوم بالبحث فوراً "
            "وتزويدك بأفضل الخيارات المتاحة",
        )
        send_buttons(sender, "أنا جاهز للبحث لك. ما هو المنتج الذي تريده", [
            {"id": "category_kitchen", "title": "أدوات مطبخ"},
            {"id": "category_electronics", "title": "إلكترونيات"},
            {"id": "category_cleaning", "title": "منظفات"},
        ])
        return

    if raw_action == "category_kitchen" or msg_normalized == normalize_text("أدوات مطبخ"):
        send_message(sender, "اكتبي اسم أداة المطبخ أو الفئة التي تبحثين عنها، وسأبحث لكِ عنها فوراً 😊")
        return

    if raw_action in {"category_electronics", "category_cleaning"} or msg_normalized in {
        normalize_text("إلكترونيات"),
        normalize_text("منظفات"),
    }:
        send_message(sender, "سيتم توفير المنتجات قريباً 😊")
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

    if raw_action == "menu_offers" or msg_normalized == "menuoffers":
        send_offers_response(sender)
        return

    order_number_in_message = extract_order_number(msg_body)
    if (
        is_order_detail_inquiry(msg_normalized)
        or order_number_in_message
        or (order_number_in_message and any(word in msg_normalized for word in ["تفاصيل", "حاله", "حالة", "تتبع", "وضع"]))
    ):
        if order_number_in_message:
            order = customer_order_by_number(sender, order_number_in_message)
            if not order:
                send_message(sender, f"❌ لم أجد طلباً بهذا الرقم: {order_number_in_message}")
            else:
                send_customer_order_details(sender, order)
        else:
            send_customer_order_details(sender, latest_customer_order(sender))
        return

    if is_payment_status_inquiry(msg_normalized):
        send_customer_payment_status(sender)
        return

    if is_cancel_order_request(msg_normalized):
        request_order_cancellation(sender, order_number_in_message)
        return

    if is_address_update_request(msg_normalized):
        request_address_update(sender)
        return

    if is_order_edit_request(msg_normalized):
        request_order_edit(sender)
        return

    if is_customer_complaint(msg_normalized):
        request_customer_complaint(sender)
        return

    # أسئلة الطلبات تُعرض من قاعدة البيانات مباشرة ولا تُعامل كبحث عن منتج.
    if is_order_inquiry(msg_normalized):
        send_customer_orders(sender)
        return

    if is_price_inquiry(msg_normalized):
        send_price_inquiry_response(sender)
        return

    if is_offers_inquiry(msg_normalized):
        send_offers_response(sender)
        return

    # ╔══════════════════════════════════════════════════════════╗
    # ║     البحث الموحد في كل الردود (مبرمجة + مخصصة)         ║
    # ╚══════════════════════════════════════════════════════════╝

    if is_positive_social_message(msg_normalized):
        send_contextual_praise_reply(sender)
        return

    if is_social_or_confused_message(msg_normalized):
        social_intro = "ههههه منورة 😊" if "ه" in msg_normalized else "أنا معك يا غالية 😊"
        if msg_normalized in {normalize_text("احبك"), normalize_text("احبج")}:
            social_intro = "شكراً لكِ يا غالية، لطفك أسعدني 😊"
        elif msg_normalized in {normalize_text("مافهمت"), normalize_text("ما فهمت"), normalize_text("ايش"), normalize_text("وش")}:
            social_intro = "ولا يهمك يا غالية، أبشرح لكِ بطريقة أبسط 😊"
        send_guided_help(sender, social_intro)
        return

    # سؤال العميل عن طريقة الكتابة لا يمثل اسم منتج؛ نجيب بأمثلة قبل أي بحث أو فهم دلالي.
    if is_search_examples_request(msg_normalized):
        send_search_examples(sender)
        return

    # التحقق من التحيات والكلمات القصيرة قبل البحث المباشر في المنتجات حتى لا تُعامل كلمة "هلا" أو التحيات كبحث عن منتج
    response_data = find_response(msg_normalized)
    if response_data:
        send_response(sender, response_data)
        return

    # === البحث في المنتجات (قاعدة البيانات) أولاً لضمان عدم ضياع أي منتج جديد في الفهم الدلالي ===
    products = get_all_products()
    matching = []
    search_terms = product_search_terms(msg_normalized)
    corrected_query = correct_search_spelling(msg_normalized)
    query_tokens = {
        token for token in corrected_query.split()
        if len(token) >= 3 and token not in SEARCH_STOPWORDS
    }
    for p in products:
        p_name = normalize_text(p['name'])
        p_keywords = normalize_text(p.get('keywords', '') or '')
        p_description = normalize_text(p.get('description', '') or '')
        searchable_text = _searchable_product_text(p)
        if any(term in p_name or p_name in term for term in search_terms):
            matching.append(p)
        elif any(term in searchable_text for term in search_terms if len(term) >= 3):
            matching.append(p)
        elif p_keywords:
            kw_list = [normalize_text(k.strip()) for k in p_keywords.split(",")]
            for kw in kw_list:
                if kw and any(term in kw or kw in term for term in search_terms):
                    matching.append(p)
                    break
        if p not in matching and query_tokens:
            product_tokens = set(searchable_text.split())
            fuzzy_hits = sum(_fuzzy_token_match(token, product_tokens) for token in query_tokens)
            if fuzzy_hits >= 1 and (len(query_tokens) == 1 or fuzzy_hits >= 2):
                matching.append(p)

    if len(matching) == 1:
        found = matching[0]
        send_product_card(sender, found)
        return
    elif len(matching) > 1:
        send_matching_products_carousel(sender, matching, msg_normalized)
        return

    # المحادثة العامة وفهم السياق والفهم الدلالي للاستفسارات العامة التي ليست بحثاً مباشراً عن منتج
    semantic_result = None
    try:
        semantic_result = interpret_customer_message(sender, msg_body)
    except Exception as exc:
        print(f"[الذكاء] تعذر فهم رسالة العميل دلالياً: {exc}")
    if route_semantic_intent(sender, msg_body, semantic_result, products):
        return

    # (تم التحقق مسبقاً من find_response أولاً لمنع الخلط مع التحيات)

    # لا نعيد سؤال التوضيح الطويل مع كل رسالة غير مطابقة؛ نرد مرة واحدة
    # حسب نية الرسالة ثم نفتح إجراءً واضحاً للعميل.
    if msg_normalized and not is_low_information_query(msg_normalized):
        send_conversational_recovery(sender, msg_normalized, semantic_result)
        return

    # === الرد الذكي الاحتياطي للاستفسارات القصيرة غير المكتملة ===
    try:
        smart_reply = generate_smart_reply(sender, msg_body)
    except Exception as exc:
        print(f"[الذكاء] تعذر إنشاء الرد الذكي: {exc}")
        smart_reply = None
    if smart_reply:
        send_message(sender, smart_reply)
        return

    # === رد افتراضي عند عدم توفر خدمة الذكاء ===
    send_guided_help(
        sender,
        "أنا معك يا غالية 😊 ما وصلني طلب واضح. اكتبي اسم المنتج أو اختاري الخدمة المناسبة.",
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║                    Webhook Routes                           ║
# ╚══════════════════════════════════════════════════════════════╝

def process_customer_image_in_background(sender, msg_body, msg_normalized, message, message_id, message_event_id):
    """معالجة صورة العميل خارج طلب webhook حتى لا ينتهي عامل Render أثناء التحليل."""
    try:
        whatsapp.mark_as_read(message_id)
        whatsapp.send_typing_indicator(message_id)
        if msg_body:
            notify_owner(sender, msg_body, message_event_id=message_event_id)
        deliver_pending_replies(sender)
        handle_customer_message(sender, msg_body, msg_normalized, message)
    except Exception as exc:
        print(f"[الصورة] خطأ في العامل الخلفي لمعالجة الصورة: {exc}")
        try:
            image_id = (message.get("image") or {}).get("id", "")
            notify_owner_unavailable_product(
                sender,
                msg_body or "تعذر تحليل صورة المنتج",
                source="image",
                image_id=image_id,
            )
            send_unavailable_image_response(sender)
        except Exception as fallback_exc:
            print(f"[الصورة] تعذر إرسال الرد الاحتياطي للصورة: {fallback_exc}")
    finally:
        persist_customer_session(sender)
        active_message_events.pop(sender, None)

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
    if APP_SECRET:
        received_signature = request.headers.get("X-Hub-Signature-256", "")
        expected_signature = "sha256=" + hmac.new(
            APP_SECRET.encode("utf-8"), request.get_data(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(received_signature, expected_signature):
            print("[Webhook] تم رفض طلب بتوقيع غير صالح")
            return jsonify({"status": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
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
        if message_id in processed_messages or not claim_processed_webhook_message(message_id, now_ts):
            return jsonify({"status": "ok"}), 200
        processed_messages[message_id] = now_ts
        old_keys = [k for k, v in processed_messages.items() if now_ts - v > DEDUP_WINDOW]
        for k in old_keys:
            del processed_messages[k]

        record_contact(sender)

        # استخراج النص
        msg_body = ""
        processing_message = message
        if message.get("type") == "text":
            msg_body = message.get("text", {}).get("body", "").strip()
        elif message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                button_reply = interactive.get("button_reply", {})
                msg_body = button_reply.get("id") or button_reply.get("title", "")
            elif interactive.get("type") == "list_reply":
                list_reply = interactive.get("list_reply", {})
                msg_body = list_reply.get("id") or list_reply.get("title", "")
        elif message.get("type") == "button":
            # أزرار quick reply داخل الكاروسيل تصل من واتساب بنوع button
            # وpayload يحتوي المعرّف نفسه مثل variants_123 أو det_123.
            button = message.get("button", {}) or {}
            msg_body = button.get("payload") or button.get("text", "")
        elif message.get("type") == "image":
            msg_body = message.get("image", {}).get("caption", "").strip()
        elif message.get("type") == "document":
            # بعض العملاء يرسلون صورة المنتج كملف/مستند بدلاً من نوع image.
            # نحوّل الصور فقط إلى مسار المطابقة البصرية ولا نرسل رسالة عامة مضللة.
            document = message.get("document", {}) or {}
            mime_type = str(document.get("mime_type") or "").lower()
            filename = str(document.get("filename") or "").lower()
            is_image_document = mime_type.startswith("image/") or filename.endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            )
            if is_image_document and document.get("id"):
                msg_body = str(document.get("caption") or "").strip()
                processing_message = dict(message)
                processing_message["type"] = "image"
                processing_message["image"] = {
                    "id": document.get("id"),
                    "caption": msg_body,
                    "mime_type": mime_type or "image/jpeg",
                }
            else:
                recent_product = (user_sessions.get(sender, {}) or {}).get("last_product")
                if recent_product:
                    send_buttons(sender, "إذا تريدين هذا المنتج، اختاري الإجراء المناسب:", [
                        {"id": f"variants_{recent_product['id']}", "title": "📏 اختيار الحجم"}
                        if product_variants(recent_product)
                        else {"id": f"add_{recent_product['id']}", "title": "🛒 إضافة للسلة"},
                        {"id": "menu_cart", "title": "🛍️ عرض السلة"},
                    ])
                else:
                    send_message(sender, "📎 أرسلي صورة المنتج أو اكتبي اسمه، وسأساعدكِ فوراً 😊")
                return jsonify({"status": "ok"}), 200
        elif message.get("type") == "audio":
            try:
                msg_body = transcribe_voice_message(message) or ""
            except RuntimeError as exc:
                if str(exc) == "VOICE_BUSY":
                    send_message(sender, "🎙️ ما زلت أعالج رسالة صوتية سابقة، انتظري لحظات ثم أرسلي التسجيل مرة أخرى 😊")
                elif str(exc) == "VOICE_DUPLICATE":
                    send_message(sender, "🎙️ تم استلام هذا التسجيل مسبقاً، أرسلي تسجيلاً جديداً إذا احتجتِ 😊")
                else:
                    print(f"[الصوت] خطأ في معالجة التسجيل: {exc}")
                    send_message(sender, "🎙️ الخدمة مشغولة حالياً. انتظري دقيقة ثم أرسلي التسجيل مرة أخرى 😊")
                return jsonify({"status": "ok"}), 200
            except requests.HTTPError as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code == 429:
                    print("[الصوت] استمر 429 بعد إعادة المحاولة")
                    send_message(
                        sender,
                        "🎙️ خدمة فهم الصوت مشغولة حالياً. انتظري دقيقة واحدة ثم أرسلي التسجيل مرة أخرى 😊",
                    )
                else:
                    print(f"[الصوت] فشل طلب خدمة الصوت HTTP {status_code}: {exc}")
                    send_message(
                        sender,
                        "🎙️ تعذر فهم التسجيل حالياً. أرسليه مرة أخرى أو اكتبي طلبك نصاً من فضلكِ 😊",
                    )
                return jsonify({"status": "ok"}), 200
            except Exception as exc:
                print(f"[الصوت] تعذر تفريغ الرسالة الصوتية: {exc}")
                send_message(
                    sender,
                    "🎙️ وصلتني رسالتك الصوتية، لكن تعذر فهم التسجيل حالياً. "
                    "أرسليها مرة أخرى أو اكتبي طلبك نصاً من فضلكِ 😊",
                )
                return jsonify({"status": "ok"}), 200
            if not msg_body:
                send_message(sender, "🎙️ لم أتمكن من سماع كلمات واضحة في التسجيل. أرسليه مرة أخرى من فضلكِ 😊")
                return jsonify({"status": "ok"}), 200
            # بعد التفريغ نعامل الصوت كنص حتى تعمل حالات الاسم والعنوان والطلب بشكل طبيعي.
            processing_message = dict(message)
            processing_message["type"] = "text"
            processing_message["text"] = {"body": msg_body}
        else:
            # لا نرسل رسالة عامة هنا؛ أنواع واتساب غير المدعومة قد تأتي بجانب
            # ضغطات الأزرار أو بطاقات المنتج، والرد العام يربك مسار الشراء.
            print(f"[Webhook] تم تجاهل نوع رسالة غير مدعوم: {message.get('type', '')}")
            return jsonify({"status": "ok"}), 200

        msg_normalized = normalize_text(msg_body)
        original_message_type = message.get("type", "text")
        image_payload = processing_message.get("image", {}) if processing_message.get("type") == "image" else {}
        audio_payload = message.get("audio", {}) if original_message_type == "audio" else {}
        intent, intent_confidence = classify_message_intent(
            msg_body,
            original_message_type,
        )
        message_event_id = record_message_event(
            whatsapp_message_id=message_id,
            direction="inbound",
            phone_number=sender,
            message_type=original_message_type,
            body=msg_body,
            normalized_body=msg_normalized,
            caption=image_payload.get("caption", "") if image_payload else "",
            media_id=image_payload.get("id", "") or audio_payload.get("id", ""),
            intent=intent,
            intent_confidence=intent_confidence,
        )
        active_message_events[sender] = message_event_id

        # تطبيع رقم المرسل ورقم الإدارة لمقارنة آمنة بغض النظر عن الـ + أو الفراغات
        clean_sender = str(sender).strip().lstrip("+")
        clean_owner = str(OWNER_NUMBER).strip().lstrip("+")
        is_owner = (clean_sender == clean_owner or clean_sender.endswith(clean_owner) or clean_owner.endswith(clean_sender))

        # تحليل صورة المنتج قد يتجاوز مهلة عامل Gunicorn بسبب تنزيل الصورة ومطابقة
        # الكتالوج وطلب التحليل الذكي. لذلك نعيد 200 لواتساب فوراً ثم نعالج الصورة
        # في عامل خلفي، فلا تتكرر الرسالة ولا يُقتل عامل البوت أثناء المعالجة.
        if processing_message.get("type") == "image" and not is_owner:
            Thread(
                target=process_customer_image_in_background,
                args=(sender, msg_body, msg_normalized, processing_message, message_id, message_event_id),
                daemon=True,
                name=f"image-{message_id[-8:]}",
            ).start()
            return jsonify({"status": "ok"}), 200

        # جاري القراءة والكتابة للرسائل الخفيفة فقط؛ معالجة الصورة تتم في العامل الخلفي.
        whatsapp.mark_as_read(message_id)
        whatsapp.send_typing_indicator(message_id)

        # معالجة أزرار الإدارة أوامر المالك أو الرد المقتبس للإدارة أولاً وقبل أي شيء
        if is_owner:
            handle_owner_command(sender, msg_body, msg_normalized, processing_message)
            active_message_events.pop(sender, None)
            return jsonify({"status": "ok"}), 200

        # إشعار المالك للرسائل الفعلية للعملاء فقط
        if msg_body and original_message_type != "interactive":
            notify_owner(sender, msg_body, message_event_id=message_event_id)

        # معالجة رسائل العملاء فقط
        voice_mode_token = None
        voice_sent_token = None
        if original_message_type == "audio":
            voice_mode_token = voice_reply_mode.set(True)
            voice_sent_token = voice_reply_sent.set(False)
        try:
            deliver_pending_replies(sender)
            handle_customer_message(sender, msg_body, msg_normalized, processing_message)
        finally:
            if voice_sent_token is not None:
                voice_reply_sent.reset(voice_sent_token)
            if voice_mode_token is not None:
                voice_reply_mode.reset(voice_mode_token)
            persist_customer_session(sender)
            active_message_events.pop(sender, None)

    except (KeyError, IndexError):
        pass
    except Exception as e:
        print(f"خطأ: {e}")

    return jsonify({"status": "ok"}), 200


def _dashboard_token_is_valid():
    """حماية واجهة اللوحة بتوكن خادم لا يظهر داخل كود الموقع."""
    configured = os.environ.get("DASHBOARD_API_TOKEN", "").strip()
    supplied = request.headers.get("X-Titiz-Admin-Token", "").strip()
    return bool(configured and supplied and hmac.compare_digest(supplied, configured))


def _dashboard_cors(response):
    origin = request.headers.get("Origin", "")
    allowed_origin = os.environ.get("DASHBOARD_ORIGIN", "").strip()
    if allowed_origin and origin == allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Titiz-Admin-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.route("/admin/api/messages", methods=["GET", "OPTIONS"])
def dashboard_messages():
    if request.method == "OPTIONS":
        return _dashboard_cors(make_response("", 204))
    if not _dashboard_token_is_valid():
        return _dashboard_cors(jsonify({"error": "unauthorized"})), 401
    try:
        limit = request.args.get("limit", 100, type=int)
        rows = get_message_events(
            limit=limit,
            phone_number=request.args.get("phone") or None,
            intent=request.args.get("intent") or None,
        )
        return _dashboard_cors(jsonify({"messages": rows, "count": len(rows)}))
    except Exception as exc:
        print(f"[لوحة الإدارة] تعذر قراءة الرسائل: {exc}")
        return _dashboard_cors(jsonify({"error": "messages_unavailable"})), 500


@app.route("/admin/api/summary", methods=["GET", "OPTIONS"])
def dashboard_summary():
    if request.method == "OPTIONS":
        return _dashboard_cors(make_response("", 204))
    if not _dashboard_token_is_valid():
        return _dashboard_cors(jsonify({"error": "unauthorized"})), 401
    rows = get_message_events(limit=500)
    intents = {}
    for row in rows:
        key = row.get("intent") or "unknown"
        intents[key] = intents.get(key, 0) + 1
    return _dashboard_cors(jsonify({
        "messages_total": len(rows),
        "inbound_total": sum(1 for row in rows if row.get("direction") == "inbound"),
        "outbound_total": sum(1 for row in rows if row.get("direction") == "outbound"),
        "intents": intents,
    }))


@app.route("/admin/api/products", methods=["GET", "OPTIONS"])
def dashboard_products():
    if request.method == "OPTIONS":
        return _dashboard_cors(make_response("", 204))
    if not _dashboard_token_is_valid():
        return _dashboard_cors(jsonify({"error": "unauthorized"})), 401
    products = get_all_products()
    return _dashboard_cors(jsonify({"products": products, "count": len(products)}))

@app.route("/", methods=["GET"])
def home():
    return f"✅ {BOT_NAME} يعمل بنجاح!", 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

start_product_followup_worker()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


def sync_orders_to_github():
    """حفظ جميع الطلبات الحالية على orders.json في GitHub لضمان بقائها عند إعادة تشغيل Render."""
    try:
        if not GITHUB_TOKEN:
            return False
        remote_data, sha = github_load("orders.json")
        orders_dict = {}
        if isinstance(remote_data, dict):
            orders_dict = remote_data
        elif isinstance(remote_data, list):
            for item in remote_data:
                if isinstance(item, dict) and item.get("order_number"):
                    orders_dict[item["order_number"]] = item

        all_orders = get_orders(limit=10000)
        for order in all_orders:
            num = order.get("order_number")
            if num:
                orders_dict[num] = {
                    "order_number": num,
                    "phone_number": order.get("phone_number") or "",
                    "customer_name": order.get("customer_name") or "",
                    "address": order.get("address") or "",
                    "products_data": order.get("products_data") or [],
                    "total_price": order.get("total_price") or 0,
                    "payment_method": order.get("payment_method") or "",
                    "order_status": order.get("order_status") or "جديد",
                    "payment_proof_url": order.get("payment_proof_url") or "",
                    "created_at": order.get("created_at") or "",
                    "updated_at": order.get("updated_at") or ""
                }

        if not orders_dict:
            return False

        result = github_save("orders.json", orders_dict, sha=sha)
        if result:
            print(f"[GitHub] تم حفظ {len(orders_dict)} طلب بنجاح في orders.json")
        return result
    except Exception as e:
        print(f"[GitHub] خطأ في حفظ الطلبات: {e}")
        return False

def load_orders_from_github():
    """استعادة الطلبات المحفوظة في orders.json إلى قاعدة البيانات المحلية عند الإقلاع."""
    try:
        data, _ = github_load("orders.json")
        records = []
        if isinstance(data, dict):
            records = data.values()
        elif isinstance(data, list):
            records = data

        restored = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            num = record.get("order_number")
            phone = record.get("phone_number")
            if not num or not phone:
                continue

            # التأكد من وجود العميل أولاً
            cust = get_customer(phone)
            if not cust:
                add_customer(phone, record.get("customer_name") or "عميل واتساب", record.get("address") or "")
                cust = get_customer(phone)
            if not cust:
                continue

            cust_id = cust["id"]
            existing = get_order(num)
            if not existing:
                with db_lock:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO orders 
                        (order_number, customer_id, products_data, total_price, payment_method, order_status, payment_proof_url, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        num,
                        cust_id,
                        json.dumps(record.get("products_data") or [], ensure_ascii=False),
                        record.get("total_price") or 0,
                        record.get("payment_method") or "نقداً عند الاستلام",
                        record.get("order_status") or "جديد",
                        record.get("payment_proof_url") or "",
                        record.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        record.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()
                    conn.close()
                restored += 1
        print(f"[بدء التشغيل] تم استعادة {restored} طلب من orders.json")
    except Exception as e:
        print(f"[بدء التشغيل] خطأ في استعادة الطلبات: {e}")

# تسجيل الحفظ التلقائي قبل استعادة الطلبات أو استقبال أي رسالة.
set_order_sync_callback(sync_orders_to_github)

# استعادة الكتالوج أولاً حتى لا تبقى منتجات GitHub الجديدة غير موجودة في SQLite بعد إعادة التشغيل.
# بعدها تُستعاد الطلبات وتُرفع أي تغييرات محلية لم تكن على GitHub.
load_products_from_github()
load_orders_from_github()
sync_orders_to_github()
