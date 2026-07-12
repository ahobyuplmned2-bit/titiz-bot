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
RESP_GREETING = "أهلاً وسهلاً فيكِ يا غالية! 💛\nنورتي *Titiz* للأدوات المنزلية 🏠✨\n\nعندنا كل اللي يخلي بيتك أجمل ومطبخك أنيق! ✨\n\n🔥 *الأكثر طلباً هالأيام:*\n\n🍲 *طقم قدور ستانلس هندي* - ثقيل وشكله راقي\n   من 2,500 ريال بس\n\n☕ *ثلاجة شاي أنيقة* - ألوان حلوة تناسب الضيافة\n   2,500 ريال فقط\n\n🚚 التوصيل *مجاني* لباب بيتك!\n💳 الدفع عند الاستلام - بدون أي مخاطرة!\n\nاكتبي *قدور* أو *ثلاجة* وشوفي الصور والتفاصيل 😍\n\n💡 *الكمية محدودة والبنات طالبين كثير!* لا تفوتكِ"

RESPONSES = {
    "1": "🏠 *المنتجات والأسعار:*\n\nنوفر تشكيلة واسعة من الأدوات المنزلية:\n\n🔴 *فرامة الضغطة الذكية (المائدة MD-5266):*\n- شفرات فولاذية ضد الصدأ\n- قوة إضافية لتوفير الوقت 60%\n- سهلة الاستخدام\n- السعر: 2,800 ريال\n\n🍲 *طقم قدور المائدة 4 قطع - هندي:*\n- ستانلس ثقيل + أغطية استيل\n- 4 مقاسات: كبير/وسط/صغير/صغير جداً\n- ضمان المائدة\n- الكبير 3,500 | الوسط 3,000 | الصغير 2,500 | الصغير جداً 2,000\n- 🎁 الطقم كامل: 10,500 ريال (وفر 1,000)\n\n☕ *ثلاجة شاي المائدة M213 - 0.7 لتر:*\n- تحفظ الحرارة 6 ساعات\n- الألوان: وردي | بيج | أزرق | كحلي\n- تصميم أنيق للضيافة\n- السعر: 2,500 ريال\n\n📦 التوصيل مجاني داخل المحافظة!\nللمزيد من المنتجات تواصل معنا.\n\nأرسل *قدور* لتفاصيل طقم القدور\nأرسل *ثلاجة* لتفاصيل ثلاجة الشاي",
    "2": "🛒 *طريقة الطلب:*\nيمكنك الطلب عبر:\n1. إرسال اسم المنتج أو صورته هنا.\n2. تزويدنا بالاسم والعنوان.\n3. اختيار وسيلة الدفع (عند الاستلام أو تحويل).\n\n📦 التوصيل مجاني داخل المحافظة!",
    "3": "🚚 *التوصيل والشحن:*\n- التوصيل داخل محافظة إب: *مجاني* ✅\n- الشحن لباقي المحافظات: 2-4 أيام.",
    "4": "🔄 *سياسة الاستبدال والاسترجاع:*\n- الاستبدال خلال 7 أيام من تاريخ الاستلام.\n- الاسترجاع خلال 3 أيام بشرط أن يكون المنتج بحالته الأصلية.",
    "5": "⏰ *مواعيد العمل:*\nمن السبت إلى الخميس:\n- الفترة الصباحية: 9:00 ص - 12:00 م\n- الفترة المسائية: 4:00 م - 10:00 م\nالجمعة: من 4:00 م - 10:00 م",
    "6": "📍 *الموقع والتواصل:*\n- الموقع: إب، اليمن\n- هاتف: +967 773 595 571\n- واتساب: +967 717 864 522\n\nمحل Titiz لبيع وتوزيع جميع الأدوات المنزلية",
    "قدور": RESP_QUDOR,
    "القدور": RESP_QUDOR,
    "قدر": RESP_QUDOR,
    "طقم قدور": RESP_QUDOR,
    "ثلاجة": RESP_THALAJA,
    "ثلاجه": RESP_THALAJA,
    "الثلاجة": RESP_THALAJA,
    "الثلاجه": RESP_THALAJA,
    "شاي": RESP_THALAJA,
    "ثلاجة شاي": RESP_THALAJA,
    "اطلب": RESP_ORDER,
    "طلب": RESP_ORDER,
    "اريد اطلب": RESP_ORDER,
    "ابي اطلب": RESP_ORDER,
    "هلا": RESP_GREETING,
    "هلا والله": RESP_GREETING,
    "مرحبا": RESP_GREETING,
    "مرحبه": RESP_GREETING,
    "السلام عليكم": RESP_GREETING,
    "السلام": RESP_GREETING,
    "سلام": RESP_GREETING,
    "كيف الحال": RESP_GREETING,
    "كيفك": RESP_GREETING,
    "اهلا": RESP_GREETING,
    "اهلين": RESP_GREETING,
    "هاي": RESP_GREETING,
    "مساء الخير": RESP_GREETING,
    "صباح الخير": RESP_GREETING,
    "يعطيك العافيه": RESP_GREETING,
    "يعطيك العافية": RESP_GREETING,
}

# Keywords that trigger image responses
QUDOR_KEYWORDS = ["قدور", "القدور", "قدر", "طقم قدور"]
THALAJA_KEYWORDS = ["ثلاجة", "ثلاجه", "الثلاجة", "الثلاجه", "شاي", "ثلاجة شاي"]

WELCOME_MESSAGE = """أهلاً بك في *Titiz لبيع وتوزيع جميع الأدوات المنزلية* 🏠✨

يسعدنا خدمتك! يرجى اختيار رقم الخدمة المطلوبة:

1️⃣ الأسعار والمنتجات المتوفرة
2️⃣ طريقة الطلب
3️⃣ التوصيل والشحن
4️⃣ سياسة الاستبدال والاسترجاع
5️⃣ مواعيد العمل
6️⃣ الموقع والتواصل

📦 توصيل مجاني داخل المحافظة!

أرسل رقم الخيار للرد التلقائي.
أو اكتب: *قدور* | *ثلاجة* | *اطلب*"""


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
                # Send image if keyword matches a product
                if msg_body in QUDOR_KEYWORDS:
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
