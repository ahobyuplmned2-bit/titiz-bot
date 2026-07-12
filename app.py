from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

ACCESS_TOKEN = "EAAVV1mNUcEkBRZCKz7cZAPn3Dc0NE33WUQm7kjSQ6bLJzT7iA0IswVwteUoSHInm2aW690MiEPT87UjciE9c5Bk0VQl9cMZBloQZCF3u4bZAEFrXCqrikv68EnaOPaZAZBAQXEhfCpWWNXGP68E5DPqxUa4hP5ZBeiVTqsnQZADrEHAR8zqESGtZAtn2EXWxZBI3QZDZD"
PHONE_NUMBER_ID = "1097018736835171"
VERIFY_TOKEN = "bot_adawat_manziliya_2026"
OWNER_NUMBER = "967773595571"  # رقم المالك لاستقبال الإشعارات

# Image URLs for products
IMG_QUDOR = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/FErlTSZcVDmLLuCl.jpg"
IMG_THALAJA = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/yCftQDzESzArGegt.jpg"

# قائمة الزبائن اللي راسلوا البوت
customers = []

# Product responses
RESP_QUDOR = "🍲 *طقم قدور المائدة 4 قطع - هندي*\n\n✅ ستانلس ثقيل + أغطية استيل\n✅ 4 مقاسات: كبير/وسط/صغير/صغير جداً\n✅ ضمان المائدة\n\n💰 *الأسعار:*\nالكبير 3,500 | الوسط 3,000\nالصغير 2,500 | الصغير جداً 2,000\n\n🎁 *الطقم كامل:* 10,500 ريال - وفر 1,000\n🚚 توصيل مجاني لداخل المحافظة\n\nاكتب *اطلب* للطلب"
RESP_THALAJA = "☕ *ثلاجة شاي المائدة M213 - 0.7 لتر*\n\n✅ تحفظ الحرارة 6 ساعات\n✅ الألوان: وردي 💗 | بيج 🤎 | أزرق 💙 | كحلي\n✅ تصميم أنيق للضيافة\n\n💰 السعر: 2,500 ريال\n\n🚚 توصيل مجاني لداخل المحافظة\n⏰ الكمية محدودة\n\nاكتب *اطلب* للطلب"
RESP_ORDER = "🛒 *لإتمام الطلب:*\n\nأرسل لنا:\n1. اسم المنتج اللي تبيه\n2. اسمك الكامل\n3. عنوان التوصيل\n4. رقم تواصل آخر (اختياري)\n\n💳 الدفع عند الاستلام\n📦 التوصيل مجاني داخل المحافظة!\n\nوسيتم التواصل معك لتأكيد الطلب ✅"
# ردود التحية - بسيطة بدون ذكر منتجات
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

# رد الزبون الجديد - رسائل منفصلة
RESP_NEW_CUSTOMER = [
    "يا أهلاً وسهلاً فيكِ! 🤩💛\nشرفتينا والله! نحن سعيدين بكِ معنا ❤️\nفي *Titiz* نهتم بكل زبونة ونعاملها زي العائلة 🏠",
    "✨ *ليش تختارينا:*\n\n✅ منتجات أصلية وجودة عالية\n✅ أسعار مناسبة للجميع\n✅ توصيل مجاني لباب بيتكِ 🚚\n✅ الدفع عند الاستلام - بدون مخاطرة\n✅ استبدال خلال 7 أيام",
    "اكتبي *قدور* أو *ثلاجة* وشوفي بنفسكِ 😍\nأو اكتبي *1* لكل المنتجات\n\n💡 *زبائننا دائماً يرجعوا لنا!* 👌"
]

# رد الموقع
RESP_LOCATION = "📍 *مواقع محلات Titiz:*\n\n🏪 *الفرع الأول:*\nإب - بوابة ملعب الكبسي الخلفية\nنهاية طلعة صرافة الكريمي\n\n🏪 *الفرع الثاني:*\nالسوق المركزي القديم\nأمام صرافة فيصل الخطيب\n\n📞 للتواصل: +967 773 595 571\n✅ نستقبلكِ بأي وقت!"

RESPONSES = {
    "1": "🏠 *المنتجات والأسعار:*\n\nنوفر تشكيلة واسعة من الأدوات المنزلية:\n\n🔴 *فرامة الضغطة الذكية (المائدة MD-5266):*\n- شفرات فولاذية ضد الصدأ\n- قوة إضافية لتوفير الوقت 60%\n- سهلة الاستخدام\n- السعر: 2,800 ريال\n\n🍲 *طقم قدور المائدة 4 قطع - هندي:*\n- ستانلس ثقيل + أغطية استيل\n- 4 مقاسات: كبير/وسط/صغير/صغير جداً\n- ضمان المائدة\n- الكبير 3,500 | الوسط 3,000 | الصغير 2,500 | الصغير جداً 2,000\n- 🎁 الطقم كامل: 10,500 ريال (وفر 1,000)\n\n☕ *ثلاجة شاي المائدة M213 - 0.7 لتر:*\n- تحفظ الحرارة 6 ساعات\n- الألوان: وردي | بيج | أزرق | كحلي\n- تصميم أنيق للضيافة\n- السعر: 2,500 ريال\n\n📦 التوصيل مجاني داخل المحافظة!\nللمزيد من المنتجات تواصل معنا.\n\nأرسل *قدور* لتفاصيل طقم القدور\nأرسل *ثلاجة* لتفاصيل ثلاجة الشاي",
    "2": "🛒 *طريقة الطلب:*\nيمكنك الطلب عبر:\n1. إرسال اسم المنتج أو صورته هنا.\n2. تزويدنا بالاسم والعنوان.\n3. اختيار وسيلة الدفع (عند الاستلام أو تحويل).\n\n📦 التوصيل مجاني داخل المحافظة!",
    "3": "🚚 *التوصيل والشحن:*\n- التوصيل داخل محافظة إب: *مجاني* ✅\n- الشحن لباقي المحافظات: 2-4 أيام.",
    "4": "🔄 *سياسة الاستبدال والاسترجاع:*\n- الاستبدال خلال 7 أيام من تاريخ الاستلام.\n- الاسترجاع خلال 3 أيام بشرط أن يكون المنتج بحالته الأصلية.",
    "5": "⏰ *مواعيد العمل:*\nمن السبت إلى الخميس:\n- الفترة الصباحية: 9:00 ص - 12:00 م\n- الفترة المسائية: 4:00 م - 10:00 م\nالجمعة: من 4:00 م - 10:00 م",
    "6": RESP_LOCATION,
    # === المنتجات - القدور ===
    "قدور": RESP_QUDOR,
    "القدور": RESP_QUDOR,
    "قدر": RESP_QUDOR,
    "القدر": RESP_QUDOR,
    "طقم قدور": RESP_QUDOR,
    "طقم القدور": RESP_QUDOR,
    "قدور المائدة": RESP_QUDOR,
    "قدور المائده": RESP_QUDOR,
    "قدور هندي": RESP_QUDOR,
    "قدور ستانلس": RESP_QUDOR,
    "طقم": RESP_QUDOR,
    # === المنتجات - الثلاجة ===
    "ثلاجة": RESP_THALAJA,
    "ثلاجه": RESP_THALAJA,
    "الثلاجة": RESP_THALAJA,
    "الثلاجه": RESP_THALAJA,
    "شاي": RESP_THALAJA,
    "ثلاجة شاي": RESP_THALAJA,
    "ثلاجه شاي": RESP_THALAJA,
    "ثلاجة الشاي": RESP_THALAJA,
    "ثلاجه الشاي": RESP_THALAJA,
    "ترمس": RESP_THALAJA,
    "ترمز": RESP_THALAJA,
    "حافظة": RESP_THALAJA,
    "حافظه": RESP_THALAJA,
    # === زبون جديد ===
    "زبون": RESP_NEW_CUSTOMER,
    "زبونه": RESP_NEW_CUSTOMER,
    "زبونة": RESP_NEW_CUSTOMER,
    "عميل": RESP_NEW_CUSTOMER,
    "عميله": RESP_NEW_CUSTOMER,
    "عميلة": RESP_NEW_CUSTOMER,
    "ابي اكون زبونه": RESP_NEW_CUSTOMER,
    "ابي اكون زبونة": RESP_NEW_CUSTOMER,
    "اشتي اكون زبونه": RESP_NEW_CUSTOMER,
    "اشتي اكون زبونة": RESP_NEW_CUSTOMER,
    "اريد اكون زبونه": RESP_NEW_CUSTOMER,
    "اريد اكون زبونة": RESP_NEW_CUSTOMER,
    "بدي اكون زبونه": RESP_NEW_CUSTOMER,
    "بدي اكون زبونة": RESP_NEW_CUSTOMER,
    "زبون جديد": RESP_NEW_CUSTOMER,
    "زبونه جديده": RESP_NEW_CUSTOMER,
    "زبونة جديدة": RESP_NEW_CUSTOMER,
    "عميل جديد": RESP_NEW_CUSTOMER,
    "عميله جديده": RESP_NEW_CUSTOMER,
    "عميلة جديدة": RESP_NEW_CUSTOMER,
    "ابي اتعامل معاكم": RESP_NEW_CUSTOMER,
    "اشتي اتعامل معاكم": RESP_NEW_CUSTOMER,
    "اريد اتعامل معاكم": RESP_NEW_CUSTOMER,
    # === السؤال عن المنتجات ===
    "منتجات": RESPONSES["1"],
    "المنتجات": RESPONSES["1"],
    "بضاعة": RESPONSES["1"],
    "بضاعه": RESPONSES["1"],
    "البضاعة": RESPONSES["1"],
    "البضاعه": RESPONSES["1"],
    "ايش عندكم": RESPONSES["1"],
    "ايش معاكم": RESPONSES["1"],
    "وش عندكم": RESPONSES["1"],
    "وش معاكم": RESPONSES["1"],
    "شو عندكم": RESPONSES["1"],
    "شو معاكم": RESPONSES["1"],
    "عندكم ايش": RESPONSES["1"],
    "معاكم ايش": RESPONSES["1"],
    "ايش تبيعون": RESPONSES["1"],
    "ايش تبيعوا": RESPONSES["1"],
    "ايش فيه": RESPONSES["1"],
    "ايش في": RESPONSES["1"],
    "ايش الموجود": RESPONSES["1"],
    "ايش المتوفر": RESPONSES["1"],
    "المتوفر": RESPONSES["1"],
    "الموجود": RESPONSES["1"],
    "ابي اشوف": RESPONSES["1"],
    "ابي اشوف المنتجات": RESPONSES["1"],
    "اشتي اشوف": RESPONSES["1"],
    "اريد اشوف": RESPONSES["1"],
    "اريد اشوف المنتجات": RESPONSES["1"],
    "الاسعار": RESPONSES["1"],
    "الأسعار": RESPONSES["1"],
    "اسعار": RESPONSES["1"],
    "أسعار": RESPONSES["1"],
    "كم السعر": RESPONSES["1"],
    "كم الاسعار": RESPONSES["1"],
    "بكم": RESPONSES["1"],
    # === الموقع ===
    "الموقع": RESP_LOCATION,
    "موقع": RESP_LOCATION,
    "العنوان": RESP_LOCATION,
    "عنوان": RESP_LOCATION,
    "وينكم": RESP_LOCATION,
    "وين المحل": RESP_LOCATION,
    "وين موقعكم": RESP_LOCATION,
    "فين المحل": RESP_LOCATION,
    "فين موقعكم": RESP_LOCATION,
    "المحل": RESP_LOCATION,
    "محلكم": RESP_LOCATION,
    "مكانكم": RESP_LOCATION,
    "فينكم": RESP_LOCATION,
    "وين": RESP_LOCATION,
    "فين": RESP_LOCATION,
    "الفرع": RESP_LOCATION,
    "الفروع": RESP_LOCATION,
    "فروعكم": RESP_LOCATION,
    # === الطلب ===
    "اطلب": RESP_ORDER,
    "أطلب": RESP_ORDER,
    "طلب": RESP_ORDER,
    "اريد اطلب": RESP_ORDER,
    "أريد أطلب": RESP_ORDER,
    "اريد": RESP_ORDER,
    "أريد": RESP_ORDER,
    "ابي اطلب": RESP_ORDER,
    "أبي أطلب": RESP_ORDER,
    "ابي": RESP_ORDER,
    "أبي": RESP_ORDER,
    "ابغى": RESP_ORDER,
    "أبغى": RESP_ORDER,
    "ابغا": RESP_ORDER,
    "اشتي اطلب": RESP_ORDER,
    "اشتي": RESP_ORDER,
    "بدي اطلب": RESP_ORDER,
    "بدي": RESP_ORDER,
    "طلبيه": RESP_ORDER,
    "طلبية": RESP_ORDER,
    "اطلبي": RESP_ORDER,
    # === السلام ===
    "السلام عليكم": RESP_SALAM,
    "السلام عليكم ورحمة الله": RESP_SALAM,
    "السلام عليكم ورحمه الله": RESP_SALAM,
    "السلام عليكم ورحمة الله وبركاته": RESP_SALAM,
    "السلام": RESP_SALAM,
    "سلام": RESP_SALAM,
    "سلام عليكم": RESP_SALAM,
    "وعليكم السلام": RESP_SALAM,
    "عليكم السلام": RESP_SALAM,
    "السلام عليكم وعليكم السلام": RESP_SALAM,
    # === هلا ===
    "هلا": RESP_HALA,
    "هلا والله": RESP_HALA,
    "هلا وغلا": RESP_HALA,
    "هلاا": RESP_HALA,
    "هلااا": RESP_HALA,
    "يا هلا": RESP_HALA,
    "ياهلا": RESP_HALA,
    # === مرحبا ===
    "مرحبا": RESP_MARHABA,
    "مرحبه": RESP_MARHABA,
    "مرحباً": RESP_MARHABA,
    "مرحبأ": RESP_MARHABA,
    # === كيف الحال ===
    "كيف الحال": RESP_KAIF,
    "كيف حالك": RESP_KAIF,
    "كيفك": RESP_KAIF,
    "كيفكم": RESP_KAIF,
    "شخبارك": RESP_KAIF,
    "شخباركم": RESP_KAIF,
    "شلونك": RESP_KAIF,
    "شلونكم": RESP_KAIF,
    "اخبارك": RESP_KAIF,
    "أخبارك": RESP_KAIF,
    "اشلونك": RESP_KAIF,
    "وش اخبارك": RESP_KAIF,
    "وش أخبارك": RESP_KAIF,
    "ايش اخبارك": RESP_KAIF,
    # === اهلا ===
    "اهلا": RESP_AHLAN,
    "اهلين": RESP_AHLAN,
    "أهلا": RESP_AHLAN,
    "أهلين": RESP_AHLAN,
    "اهلاً": RESP_AHLAN,
    "أهلاً": RESP_AHLAN,
    "حياك": RESP_AHLAN,
    "حياك الله": RESP_AHLAN,
    "حياكم": RESP_AHLAN,
    "حياكم الله": RESP_AHLAN,
    # === هاي ===
    "هاي": RESP_HAI,
    "هااي": RESP_HAI,
    "hi": RESP_HAI,
    "Hi": RESP_HAI,
    "hello": RESP_HAI,
    "Hello": RESP_HAI,
    "hey": RESP_HAI,
    "Hey": RESP_HAI,
    # === مساء الخير ===
    "مساء الخير": RESP_MASA,
    "مسا الخير": RESP_MASA,
    "مساءالخير": RESP_MASA,
    "مساء الخير عليكم": RESP_MASA,
    "مسائكم خير": RESP_MASA,
    "مساكم الله بالخير": RESP_MASA,
    # === صباح الخير ===
    "صباح الخير": RESP_SABAH,
    "صباحالخير": RESP_SABAH,
    "صباح الخير عليكم": RESP_SABAH,
    "صباح النور": RESP_SABAH,
    "صباحكم خير": RESP_SABAH,
    # === يعطيك العافية ===
    "يعطيك العافيه": RESP_AFYA,
    "يعطيك العافية": RESP_AFYA,
    "الله يعافيك": RESP_AFYA,
    "الله يعافيكم": RESP_AFYA,
    "يعطيكم العافيه": RESP_AFYA,
    "يعطيكم العافية": RESP_AFYA,
    "عافيه": RESP_AFYA,
    "عافية": RESP_AFYA,
    # === شكرا ===
    "شكرا": RESP_SHUKR,
    "شكراً": RESP_SHUKR,
    "شكرا لك": RESP_SHUKR,
    "شكراً لك": RESP_SHUKR,
    "شكرا لكم": RESP_SHUKR,
    "مشكور": RESP_SHUKR,
    "مشكوره": RESP_SHUKR,
    "مشكورة": RESP_SHUKR,
    "مشكورين": RESP_SHUKR,
    "جزاك الله خير": RESP_SHUKR,
    "جزاكم الله خير": RESP_SHUKR,
    "جزاك الله خيرا": RESP_SHUKR,
    "جزاك الله خيراً": RESP_SHUKR,
    "تسلم": RESP_SHUKR,
    "تسلمي": RESP_SHUKR,
    "تسلمين": RESP_SHUKR,
    "يسلمو": RESP_SHUKR,
    "الله يجزاك خير": RESP_SHUKR,
}

# Keywords that trigger image responses
QUDOR_KEYWORDS = ["قدور", "القدور", "قدر", "القدر", "طقم قدور", "طقم القدور", "قدور المائدة", "قدور المائده", "قدور هندي", "قدور ستانلس", "طقم"]
THALAJA_KEYWORDS = ["ثلاجة", "ثلاجه", "الثلاجة", "الثلاجه", "شاي", "ثلاجة شاي", "ثلاجه شاي", "ثلاجة الشاي", "ثلاجه الشاي", "ترمس", "ترمز", "حافظة", "حافظه"]

WELCOME_MESSAGE = """يا غالية خلينا بموضوعنا 😊✨
إحنا محل *Titiz* للأدوات المنزلية 🏠

عندنا منتجات حلوة وأسعار تناسب الجميع 👌
والتوصيل مجاني لباب بيتكِ! 🚚

اكتبي *قدور* أو *ثلاجة* وشوفي الصور والأسعار 😍
أو اكتبي *1* لكل المنتجات"""


def send_message(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def send_image(to, image_url, caption=""):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def notify_owner(sender, msg_body):
    """إرسال إشعار للمالك بأن زبون راسل البوت"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    notification = f"📩 *رسالة جديدة من زبون*\n\n👤 الرقم: {sender}\n💬 الرسالة: {msg_body}\n🕐 الوقت: {now}\n\nللرد عليه مباشرة: wa.me/{sender}"
    send_message(OWNER_NUMBER, notification)


def add_customer(sender, msg_body):
    """إضافة الزبون للقائمة"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # تحقق إذا الرقم موجود مسبقاً
    for c in customers:
        if c["number"] == sender:
            c["last_message"] = msg_body
            c["last_time"] = now
            c["messages_count"] += 1
            return
    # زبون جديد
    customers.append({
        "number": sender,
        "first_message": msg_body,
        "last_message": msg_body,
        "first_time": now,
        "last_time": now,
        "messages_count": 1
    })


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def handle_message():
    data = request.get_json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            msg_body = message.get("text", {}).get("body", "").strip()

            # لا ترسل إشعار لنفسك
            if sender != OWNER_NUMBER:
                # إضافة الزبون للقائمة
                add_customer(sender, msg_body)
                # إشعار المالك
                notify_owner(sender, msg_body)

            # أمر خاص للمالك: الرد على زبون من رقم البوت
            if sender == OWNER_NUMBER and msg_body.startswith("رد "):
                parts = msg_body.split(" ", 2)
                if len(parts) == 3:
                    target_number = parts[1]
                    reply_text = parts[2]
                    send_message(target_number, reply_text)
                    send_message(OWNER_NUMBER, f"✅ تم إرسال ردك للزبون {target_number}")
                else:
                    send_message(OWNER_NUMBER, "❌ الصيغة: رد [رقم الزبون] [الرسالة]\nمثال: رد 967777123456 طلبك جاهز")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: عرض قائمة الزبائن
            if sender == OWNER_NUMBER and msg_body == "الزبائن":
                if customers:
                    customer_list = "📋 *قائمة الزبائن:*\n\n"
                    for i, c in enumerate(customers, 1):
                        customer_list += f"{i}. 👤 {c['number']}\n"
                        customer_list += f"   آخر رسالة: {c['last_message']}\n"
                        customer_list += f"   الوقت: {c['last_time']}\n"
                        customer_list += f"   عدد الرسائل: {c['messages_count']}\n\n"
                    customer_list += f"📊 إجمالي الزبائن: {len(customers)}"
                    send_message(sender, customer_list)
                else:
                    send_message(sender, "📋 لا يوجد زبائن حتى الآن.")
                return jsonify({"status": "ok"}), 200

            # الرد التلقائي
            if msg_body in RESPONSES:
                reply = RESPONSES[msg_body]
                # ردود منفصلة (قائمة)
                if isinstance(reply, list):
                    for r in reply:
                        send_message(sender, r)
                # صورة + نص
                elif msg_body in QUDOR_KEYWORDS:
                    send_image(sender, IMG_QUDOR, reply)
                elif msg_body in THALAJA_KEYWORDS:
                    send_image(sender, IMG_THALAJA, reply)
                else:
                    send_message(sender, reply)
            else:
                send_message(sender, WELCOME_MESSAGE)
    except (KeyError, IndexError):
        pass
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "✅ بوت Titiz للأدوات المنزلية يعمل بنجاح!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
