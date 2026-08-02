"""
بوت Titiz الذكي - نسخة محدثة متكاملة
تطبيق WhatsApp Bot متقدم لمتجر Titiz مع نظام السلة والطلبات والدفع
"""

from flask import Flask, request, jsonify
import requests
import json
import os
import re
import base64
from datetime import datetime
import time
from threading import Thread

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
user_sessions = {}  # حفظ قائمة المنتجات المعروضة
user_states = {}    # حالة المستخدم (في السلة، الدفع، إلخ)

# ===== منع تكرار الرسائل =====
processed_messages = {}
DEDUP_WINDOW = 30

# ===== صور المنتجات الثابتة =====
IMG_QUDOR = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/FErlTSZcVDmLLuCl.jpg"
IMG_THALAJA = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/yCftQDzESzArGegt.jpg"
IMG_FARAMA_BIG = "1722172418808924"
IMG_FARAMA_MED = "1788826688946693"
IMG_FARAMA_SML = "1340222830997132"

# ===== الردود الثابتة =====
RESP_FARAMA = "🔴 *فرامة الضغطة الذكية من المائدة* 🔪\n\nالمميزات:\n✅ توفّر عليكِ 60% من وقت التقطيع\n✅ شفرات فولاذ ضد الصدأ\n✅ سهلة التنظيف والاستخدام\n✅ تقطع كمية كبيرة مرة وحدة\n\n💰 *الأسعار:*\n🔴 الكبير (MD-5266): 3,000 ريال\n🟢 الوسط (MD-5076): 2,500 ريال\n🟢 الصغير (MD-5066): 2,000 ريال\n\n🚚 التوصيل مجاني داخل المحافظة!\n⚠️ احذروا التقليد - اطلبيها باسمها من المائدة"
RESP_QUDOR = "🍲 *طقم قدور المائدة 4 قطع - هندي*\n\n✅ ستانلس ثقيل + أغطية استيل\n✅ 4 مقاسات: كبير/وسط/صغير/صغير جداً\n✅ ضمان المائدة\n\n💰 *الأسعار:*\nالكبير 3,500 | الوسط 3,000\nالصغير 2,500 | الصغير جداً 2,000\n\n🎁 *الطقم كامل:* 10,500 ريال - وفر 1,000\n🚚 توصيل مجاني لداخل المحافظة"
RESP_THALAJA = "☕ *ثلاجة شاي المائدة M213 - 0.7 لتر*\n\n✅ تحفظ الحرارة 6 ساعات\n✅ الألوان: وردي 💗 | بيج 🤎 | أزرق 💙 | كحلي\n✅ تصميم أنيق للضيافة\n\n💰 السعر: 2,500 ريال\n\n🚚 توصيل مجاني لداخل المحافظة\n⏰ الكمية محدودة"

# ردود التحية
RESP_SALAM = "وعليكم السلام ورحمة الله 🤲✨\nنورتينا يا غالية! بايش نخدمكِ؟ 😊"
RESP_HALA = "هلا وغلا فيكِ! 💛✨\nنورتي والله! بايش نخدمكِ؟ 😊"
RESP_MARHABA = "مرحباً فيكِ! 🌸✨\nأهلاً وسهلاً! بايش نقدر نساعدكِ؟ 😊"
RESP_SABAH = "صباح النور والسعادة! ☀️🌺\nيسعد صباحكِ! بايش نخدمكِ؟ 😊"
RESP_MASA = "مساء النور والورد! 🌙✨\nأهلاً فيكِ! بايش نخدمكِ؟ 😊"
RESP_KAIF = "الحمد لله بخير! الله يسعدكِ 😊💛\nبايش نقدر نخدمكِ؟"
RESP_AFYA = "الله يعافيكِ يا قلبي! 🙏💛\nنورتينا! بايش نخدمكِ؟ 😊"
RESP_AHLAN = "أهلين فيكِ! 💛✨\nحياكِ الله! بايش نخدمكِ؟ 😊"
RESP_HAI = "هايي! 👋😊\nأهلاً فيكِ! بايش نقدر نساعدكِ؟ 💛"
RESP_SHUKR = "العفو يا غالية! 🙏✨\nإحنا في خدمتكِ دائماً! 😊"

RESP_NEW_CUSTOMER = [
    "يا أهلاً وسهلاً فيكِ! 🤩💛\nشرفتينا والله! نحن سعيدين بكِ معنا ❤️\nفي *Titiz* نهتم بكل زبونة ونعاملها زي العائلة 🏠",
    "✨ *ليش تختارينا:*\n\n✅ منتجات أصلية وجودة عالية\n✅ أسعار مناسبة للجميع\n✅ توصيل مجاني لباب بيتكِ 🚚\n✅ الدفع عند الاستلام - بدون مخاطرة\n✅ استبدال خلال 7 أيام",
    "اكتبي اسم المنتج اللي تبينه 😍\nأو اكتبي *القائمة* لعرض الخيارات 📋"
]

RESP_DELIVERY = "🚚 *التوصيل والشحن:*\n\n✅ داخل محافظة إب: *مجاني* تماماً!\n📦 باقي المحافظات: 2-4 أيام\n💳 الدفع عند الاستلام\n\nيعني ما فيه أي مخاطرة عليكِ 😊"
RESP_PAYMENT = "💳 *طرق الدفع:*\n\n✅ *الدفع عند الاستلام:*\nنحط المنتج لأقرب نقطة منكِ وتدفعي وقت الاستلام 👌\n\n✅ *التحويل المسبق:*\nتدفعي وإحنا نوصل لكِ الطلب لباب بيتكِ 🚚\n\n💰 *حسابات التحويل:*\n\n🟢 *نقطة جيب:* 906072\n🟡 *الكريمي نقطة حاسب:* 1202686\n🏦 *إيداع عبر الكريمي:* 3122678098\n\nاختاري الطريقة اللي تناسبكِ 😊"
RESP_GUARANTEE = "🔄 *الضمان والاستبدال:*\n\n✅ استبدال خلال 7 أيام من الاستلام\n✅ استرجاع خلال 3 أيام (بحالته الأصلية)\n✅ ضمان المائدة على المنتجات\n\nإحنا واثقين من جودة منتجاتنا 👌"
RESP_TRUST = "🤝 *ليش تثقين فينا:*\n\n✅ عندنا محلين في إب تقدري تزورينا 🏪\n✅ الدفع عند الاستلام - ما نطلب فلوس مقدماً\n✅ استبدال خلال 7 أيام لو ما عجبكِ\n✅ زبائننا كثير والحمد لله راضين\n✅ نشتغل بسمعتنا وما نغش أي زبون\n\n📍 *عناويننا:*\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم\n\nجربي واحكمي بنفسكِ 😊👌"
RESP_LOCATION = "📍 *مواقع محلات Titiz:*\n\n🏪 *الفرع الأول:*\nإب - بوابة ملعب الكبسي الخلفية\nنهاية طلعة صرافة الكريمي\n\n🏪 *الفرع الثاني:*\nالسوق المركزي القديم\nأمام صرافة فيصل الخطيب\n\n✅ نستقبلكِ بأي وقت!"
RESP_PRODUCTS_ASK = "🏠 أهلاً فيكِ يا غالية! ✨\n\nلدينا جميع الأدوات المنزلية ومستلزمات المطابخ 🍳\n\nايش بدكِ أنتِ من منتج؟ 😊\n\nمثلاً:\n🍲 اكتبي *قدور* - طقم قدور ستانلس\n☕ اكتبي *ثلاجة* - ثلاجة شاي أنيقة\n🔪 اكتبي *فرامة* - فرامة الضغطة الذكية\n\nأو اكتبي *القائمة* لعرض كل الخيارات 📋"
RESP_WHERE_DELIVER = "📦 وين تحبين نحط لكِ المنتج؟ 🤔\n\nنقدر نحطه في أي مكان قريب منكِ:\n\n🏪 محل قريب من بيتكِ\n🛍️ بقالة في حارتكِ\n📍 أي نقطة تحدديها\n\nأرسلي لنا اسم المكان أو المنطقة وإحنا نوصله لأقرب نقطة منكِ 😊👌"
RESP_BYE = "مع السلامة يا غالية! 💛👋\nنورتينا والله!\nإحنا هنا بأي وقت تحتاجينا 😊\nلا تنسينا! ❤️"
RESP_ORDER = "🛒 *لإتمام الطلب:*\n\nاكتبي *اكمل الطلب* وبنكمل معكِ الخطوات 😊\n\nأو أضيفي منتجات للسلة أولاً:\nاكتبي اسم المنتج وبنضيفه لكِ ✅\n\n💳 الدفع عند الاستلام أو تحويل\n📦 التوصيل مجاني داخل المحافظة!"

WELCOME_MESSAGE = "يا غالية خلينا بموضوعنا 😊✨\nإحنا محل *Titiz* للأدوات المنزلية 🏠\n\nعندنا منتجات حلوة وأسعار تناسب الجميع 👌\nوالتوصيل مجاني لباب بيتكِ! 🚚\n\nاكتبي اسم المنتج اللي تبينه 😍\nأو اكتبي *القائمة* لعرض الخيارات 📋"

# ===== قاموس الردود =====
RESPONSES = {}

# المنتجات - الفرامة
FARAMA_KEYWORDS = ["فرامة", "فرامه", "الفرامة", "الفرامه", "فرامة الضغطة", "فرامه الضغطه",
    "فرامة الضغطه", "فرامه الضغطة", "الفرامة الذكية", "الفرامه الذكيه", "فرامة ذكية",
    "فرامه ذكيه", "عصارة", "عصاره", "العصارة", "العصاره", "فرامة المائدة", "فرامه المائده",
    "فرامة المائده", "فرامه المائدة", "فرامة خضار", "فرامه خضار", "قطاعة", "قطاعه",
    "القطاعة", "القطاعه", "مفرمة", "مفرمه", "المفرمة", "المفرمه", "خلاط", "الخلاط",
    "فرامة ضغطة", "فرامه ضغطه", "ضغطة ذكية", "ضغطه ذكيه"]
for kw in FARAMA_KEYWORDS:
    RESPONSES[kw] = RESP_FARAMA

# المنتجات - القدور
QUDOR_KEYWORDS = ["قدور", "القدور", "قدر", "القدر", "طقم قدور", "طقم القدور",
    "قدور المائدة", "قدور المائده", "قدور هندي", "قدور ستانلس", "طقم",
    "قدور هندية", "قدور هنديه", "حلل", "الحلل", "طنجرة", "طنجره"]
for kw in QUDOR_KEYWORDS:
    RESPONSES[kw] = RESP_QUDOR

# المنتجات - الثلاجة
THALAJA_KEYWORDS = ["ثلاجة", "ثلاجه", "الثلاجة", "الثلاجه", "شاي", "ثلاجة شاي",
    "ثلاجه شاي", "ثلاجة الشاي", "ثلاجه الشاي", "ترمس", "ترمز", "حافظة", "حافظه",
    "ثلاجة المائدة", "ثلاجه المائده"]
for kw in THALAJA_KEYWORDS:
    RESPONSES[kw] = RESP_THALAJA

# التحية
for kw in ["السلام عليكم", "السلام وعليكم", "السلامعليكم", "السلام عليكم ورحمة الله",
           "السلام عليكم ورحمه الله", "السلام عليكم ورحمة الله وبركاته",
           "السلام عليكم ورحمه الله وبركاته", "السلام", "سلام عليكم",
           "سلام وعليكم", "وعليكم السلام", "عليكم السلام", "السلام عليك",
           "سلام عليك", "اسلام وعليكم", "اسلام عليكم", "اسلام", "اسلام عليك"]:
    RESPONSES[kw] = RESP_SALAM

for kw in ["هلا", "هلا والله", "هلا وغلا", "هلاا", "هلااا", "يا هلا", "ياهلا"]:
    RESPONSES[kw] = RESP_HALA

for kw in ["مرحبا", "مرحبه", "مرحباً", "مرحبأ"]:
    RESPONSES[kw] = RESP_MARHABA

for kw in ["كيف الحال", "كيف حالك", "كيفك", "كيفكم", "شخبارك", "شخباركم",
           "شلونك", "شلونكم", "اخبارك", "أخبارك", "اشلونك", "وش اخبارك",
           "وش أخبارك", "ايش اخبارك"]:
    RESPONSES[kw] = RESP_KAIF

for kw in ["اهلا", "اهلين", "أهلا", "أهلين", "اهلاً", "أهلاً", "حياك",
           "حياك الله", "حياكم", "حياكم الله"]:
    RESPONSES[kw] = RESP_AHLAN

for kw in ["هاي", "هااي", "hi", "hello", "hey"]:
    RESPONSES[kw] = RESP_HAI

for kw in ["مساء الخير", "مسا الخير", "مساءالخير", "مساء الخير عليكم",
           "مسائكم خير", "مساكم الله بالخير"]:
    RESPONSES[kw] = RESP_MASA

for kw in ["صباح الخير", "صباحالخير", "صباح الخير عليكم", "صباح النور", "صباحكم خير"]:
    RESPONSES[kw] = RESP_SABAH

for kw in ["يعطيك العافيه", "يعطيك العافية", "الله يعافيك", "الله يعافيكم",
           "يعطيكم العافيه", "يعطيكم العافية", "عافيه", "عافية"]:
    RESPONSES[kw] = RESP_AFYA

for kw in ["شكرا", "شكراً", "شكرا لك", "شكراً لك", "شكرا لكم", "مشكور",
           "مشكوره", "مشكورة", "مشكورين", "جزاك الله خير", "جزاكم الله خير",
           "تسلم", "تسلمي", "تسلمين", "يسلمو", "الله يجزاك خير"]:
    RESPONSES[kw] = RESP_SHUKR

# التوصيل
for kw in ["توصيل", "التوصيل", "شحن", "الشحن", "توصلون", "توصلوا", "يوصل",
           "كم التوصيل", "سعر التوصيل", "مجاني", "التوصيل مجاني"]:
    RESPONSES[kw] = RESP_DELIVERY

# الدفع
for kw in ["دفع", "الدفع", "كيف ادفع", "كيف الدفع", "طريقة الدفع", "طريقه الدفع",
           "حساب", "الحساب", "تحويل", "التحويل", "حسابات", "الحسابات", "نقطة جيب",
           "الكريمي", "كريمي", "جيب"]:
    RESPONSES[kw] = RESP_PAYMENT

# الضمان
for kw in ["ضمان", "الضمان", "استبدال", "الاستبدال", "استرجاع", "الاسترجاع",
           "ارجاع", "الارجاع", "ترجيع", "لو ما عجبني", "اذا ما عجبني"]:
    RESPONSES[kw] = RESP_GUARANTEE

# الثقة
for kw in ["ثقة", "الثقة", "مصداقية", "كيف نثق", "كيف اثق", "نثق فيكم",
           "اثق فيكم", "صادقين", "تكذبون", "نصب", "احتيال"]:
    RESPONSES[kw] = RESP_TRUST

# الموقع
for kw in ["الموقع", "موقع", "العنوان", "عنوان", "وينكم", "وين المحل",
           "وين موقعكم", "فين المحل", "فين موقعكم", "المحل", "محلكم",
           "مكانكم", "فينكم", "الفرع", "الفروع", "فروعكم"]:
    RESPONSES[kw] = RESP_LOCATION

# الطلب
for kw in ["اطلب", "أطلب", "ابي اطلب", "أبي أطلب", "ابغى", "أبغى",
           "اشتي اطلب", "بدي اطلب", "طلبيه", "طلبية"]:
    RESPONSES[kw] = RESP_ORDER

# ايش عندكم
for kw in ["ايش عندكم", "ايش معاكم", "وش عندكم", "ايش تبيعون", "ايش تبيعو",
           "ايش منتجاتكم", "وش منتجاتكم", "ايش البضاعة", "ايش البضاعه",
           "منتجات", "المنتجات", "بضاعة", "البضاعة", "البضاعه",
           "ايش في", "وش في", "عندكم ايش", "معاكم ايش"]:
    RESPONSES[kw] = RESP_PRODUCTS_ASK

# مكان الاستلام
for kw in ["وين تحطوا", "وين تحطون", "فين تحطوا", "وين توصلوا",
           "فين توصلوا", "وين اخذه", "وين اخذ الطلب", "فين اخذه",
           "وين الاستلام", "فين الاستلام", "من وين استلم",
           "الاستلام", "طريقة الاستلام", "طريقه الاستلام"]:
    RESPONSES[kw] = RESP_WHERE_DELIVER

# الوداع
for kw in ["مع السلامة", "مع السلامه", "باي", "الله يحفظك", "في أمان الله",
           "في امان الله", "يلا باي", "خلاص شكرا", "تمام شكرا"]:
    RESPONSES[kw] = RESP_BYE

# ===== دوال مساعدة =====

def normalize_text(text):
    """تطبيع النص للبحث"""
    text = text.strip().lower()
    for ch in ['!', '?', '.', ',', '؟', '،', '\u200f', '\u200e', '؛']:
        text = text.replace(ch, '')
    return text.strip()

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
    """إرسال رسالة نصية"""
    return whatsapp.send_message(to, text)

def send_image(to, image_url, caption=""):
    """إرسال صورة برابط"""
    return whatsapp.send_image(to, image_url, caption)

def send_image_by_id(to, media_id, caption=""):
    """إرسال صورة بمعرف"""
    return whatsapp.send_image_by_id(to, media_id, caption)

def send_buttons(to, text, buttons):
    """إرسال أزرار"""
    return whatsapp.send_buttons(to, text, buttons)

def send_list(to, text, button_text, sections):
    """إرسال قائمة"""
    return whatsapp.send_list(to, text, button_text, sections)

def notify_owner(sender, msg_body):
    """إشعار المالك برسالة جديدة"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    notification = f"📩 *رسالة جديدة*\n\n👤 الرقم: {sender}\n💬 الرسالة: {msg_body}\n🕐 الوقت: {now}"
    send_message(OWNER_NUMBER, notification)

def notify_owner_new_order(order_number, phone, name, address, items, total, payment_method):
    """إشعار المالك بطلب جديد"""
    items_text = ""
    for item in items:
        items_text += f"  • {item['name']} × {item.get('qty',1)} = {item.get('total',0)} ريال\n"
    msg = f"🔔 *طلب جديد!*\n\n📋 رقم الطلب: *{order_number}*\n👤 الاسم: {name}\n📱 الرقم: {phone}\n📍 العنوان: {address}\n\n🛒 *المنتجات:*\n{items_text}\n💰 *الإجمالي: {int(total)} ريال*\n💳 الدفع: {payment_method}"
    send_message(OWNER_NUMBER, msg)

# ===== القائمة التفاعلية =====
def send_main_menu(to):
    """إرسال القائمة الرئيسية"""
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

# ===== معالجة أوامر المالك =====
def handle_owner_command(sender, msg_body, msg_normalized, message):
    """معالجة أوامر المالك - ترجع True إذا تم التعامل مع الأمر"""

    # رد على زبون
    if msg_normalized.startswith("رد "):
        parts = msg_body.split(" ", 2)
        if len(parts) == 3:
            send_message(parts[1], parts[2])
            send_message(OWNER_NUMBER, f"✅ تم إرسال ردك للزبون {parts[1]}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: رد [رقم] [الرسالة]")
        return True

    # إضافة منتج
    if msg_normalized.startswith("اضف ") and not msg_normalized.startswith("اضف سؤال"):
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

    # تعديل سعر
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

    # حذف منتج
    if msg_normalized.startswith("حذف ") and not msg_normalized.startswith("حذف سؤال"):
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

    # المخزن
    if msg_normalized in ["المخزن", "مخزن", "منتجاتي"]:
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

    # إضافة سؤال
    if msg_normalized.startswith("اضف سؤال "):
        parts = msg_body.split(" ", 3)
        if len(parts) >= 4:
            save_qa(parts[2], parts[3])
            send_message(OWNER_NUMBER, f"✅ تم إضافة السؤال:\nالكلمة: {parts[2]}\nالرد: {parts[3]}")
        else:
            send_message(OWNER_NUMBER, "❌ الصيغة: اضف سؤال [الكلمة] [الرد]")
        return True

    # حذف سؤال
    if msg_normalized.startswith("حذف سؤال "):
        keyword = msg_body[10:].strip()
        delete_qa(keyword)
        send_message(OWNER_NUMBER, f"✅ تم حذف السؤال: {keyword}")
        return True

    # عرض الأسئلة
    if msg_normalized in ["الاسئلة", "اسئلة", "الاسئله", "اسئله"]:
        qas = load_qa()
        if qas:
            qa_list = "❓ *الأسئلة والأجوبة:*\n\n"
            for i, (k, v) in enumerate(qas.items(), 1):
                qa_list += f"{i}. *{k}* → {v}\n\n"
            send_message(OWNER_NUMBER, qa_list)
        else:
            send_message(OWNER_NUMBER, "❓ لا توجد أسئلة محفوظة")
        return True

    # الزبائن
    if msg_normalized in ["الزبائن", "زبائن", "عملاء", "العملاء"]:
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

    # الطلبات
    if msg_normalized in ["الطلبات", "طلبات"]:
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

    # تغيير حالة طلب
    if msg_normalized.startswith("حالة ") or msg_normalized.startswith("حاله "):
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

    # الإحصائيات
    if msg_normalized in ["إحصائيات", "احصائيات", "احصاءات", "إحصاءات", "stats"]:
        stats = get_statistics()
        msg = f"📊 *إحصائيات المتجر:*\n\n📦 إجمالي الطلبات: {stats['total_orders']}\n💰 إجمالي المبيعات: {int(stats['total_sales'])} ريال\n👥 عدد العملاء: {stats['total_customers']}"
        send_message(OWNER_NUMBER, msg)
        return True

    # نسخ احتياطي
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

    # رفع صورة لمنتج
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

# ===== معالجة رسائل العملاء =====
def handle_customer_message(sender, msg_body, msg_normalized, message):
    """معالجة رسائل العملاء"""
    state = user_states.get(sender, "")

    # === حالات الجلسة ===

    # انتظار اسم العميل
    if state == "awaiting_name":
        user_states[sender] = "awaiting_address"
        user_sessions[sender] = {"name": msg_body.strip()}
        send_message(sender, "📍 تمام! الحين أرسلي لنا عنوان التوصيل (المنطقة أو أقرب نقطة) 😊")
        return

    # انتظار العنوان
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

    # انتظار اختيار الدفع
    if state == "awaiting_payment":
        session_data = user_sessions.get(sender, {})
        if "استلام" in msg_normalized or msg_normalized == "pay_cod" or msg_normalized == "1":
            # إنشاء الطلب
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

    # انتظار صورة التحويل
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
                send_message(OWNER_NUMBER, f"📸 صورة إشعال التحويل للطلب {order_number}")
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

    # === مسح الجلسة إذا رسالة جديدة ===
    if state == "product_list" and not msg_normalized.isdigit():
        user_states.pop(sender, None)
        user_sessions.pop(sender, None)

    # === القائمة التفاعلية ===
    if msg_normalized in ["القائمة", "القائمه", "قائمة", "قائمه", "menu", "ابدا", "ابدأ", "start"]:
        send_main_menu(sender)
        return

    # === أوامر السلة ===
    if msg_normalized in ["السلة", "السله", "سلة", "سله", "عربتي", "cart", "menu_cart"]:
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

    if msg_normalized in ["افرغ السلة", "افرغ السله", "تفريغ السلة", "مسح السلة"]:
        clear_cart(sender)
        send_message(sender, "🗑️ تم تفريغ السلة ✅")
        return

    # إضافة للسلة
    if msg_normalized.startswith("اضف للسلة ") or msg_normalized.startswith("اضيف "):
        product_name = msg_body[11:].strip() if msg_normalized.startswith("اضف للسلة ") else msg_body[5:].strip()
        products = get_all_products()
        for p in products:
            if normalize_text(product_name) in normalize_text(p['name']) or normalize_text(p['name']) in normalize_text(product_name):
                add_to_cart(sender, p['id'], 1)
                send_message(sender, f"✅ تم إضافة *{p['name']}* للسلة!\n💰 السعر: {int(p['price'])} ريال\n\nاكتبي *السلة* لعرض المشتريات\nأو *اكمل الطلب* لإتمام الشراء 😊")
                return
        send_message(sender, f"❌ ما لقينا منتج باسم '{product_name}'\nجربي اسم ثاني 😊")
        return

    # إكمال الطلب
    if msg_normalized in ["اكمل الطلب", "اكمل", "تأكيد", "تاكيد", "اكمال الطلب", "checkout"]:
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
    if msg_normalized in ["طلباتي", "menu_orders"]:
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
        send_message(sender, RESP_PAYMENT)
        return
    if msg_normalized == "menu_location":
        send_message(sender, RESP_LOCATION)
        return
    if msg_normalized == "menu_contact":
        send_message(sender, "📞 *التواصل معنا:*\n\nراسلينا هنا وبنرد عليكِ بأسرع وقت 😊\n\n📍 أو زورينا في أحد فروعنا:\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم")
        return

    # === البحث في الردود الثابتة ===
    matched_key = None
    if msg_normalized in RESPONSES:
        matched_key = msg_normalized
    else:
        for key in RESPONSES:
            if len(key) > 2 and key in msg_normalized:
                matched_key = key
                break

    if matched_key:
        reply = RESPONSES[matched_key]
        if isinstance(reply, list):
            for r in reply:
                send_message(sender, r)
        elif matched_key in FARAMA_KEYWORDS:
            send_message(sender, reply)
            send_image_by_id(sender, IMG_FARAMA_BIG, "🔴 الكبير MD-5266 - 3,000 ريال")
            send_image_by_id(sender, IMG_FARAMA_MED, "🟢 الوسط MD-5076 - 2,500 ريال")
            send_image_by_id(sender, IMG_FARAMA_SML, "🟢 الصغير MD-5066 - 2,000 ريال")
        elif matched_key in QUDOR_KEYWORDS:
            send_image(sender, IMG_QUDOR, reply)
        elif matched_key in THALAJA_KEYWORDS:
            send_image(sender, IMG_THALAJA, reply)
        else:
            send_message(sender, reply)
        return

    # === البحث في المنتجات (قاعدة البيانات) ===
    products = get_all_products()
    matching = []
    for p in products:
        p_name = normalize_text(p['name'])
        p_keywords = normalize_text(p.get('keywords', '') or '')
        if msg_normalized in p_name or p_name in msg_normalized:
            matching.append(p)
        elif p_keywords and (msg_normalized in p_keywords):
            matching.append(p)

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

    # === البحث في الأسئلة والأجوبة ===
    qas = load_qa()
    for qa_key, qa_answer in qas.items():
        if qa_key in msg_normalized or msg_normalized in qa_key:
            send_message(sender, qa_answer)
            return

    # === رد افتراضي ===
    send_message(sender, WELCOME_MESSAGE)

# ===== Webhook Routes =====

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """التحقق من webhook"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """معالج webhook لاستقبال الرسائل"""
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

        # تأخير بسيط (مؤشر كتابة)
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
    """الصفحة الرئيسية"""
    return f"✅ {BOT_NAME} يعمل بنجاح!", 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
