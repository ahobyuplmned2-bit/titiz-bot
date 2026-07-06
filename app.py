from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

ACCESS_TOKEN = "EAAVV1mNUcEkBRZCKz7cZAPn3Dc0NE33WUQm7kjSQ6bLJzT7iA0IswVwteUoSHInm2aW690MiEPT87UjciE9c5Bk0VQl9cMZBloQZCF3u4bZAEFrXCqrikv68EnaOPaZAZBAQXEhfCpWWNXGP68E5DPqxUa4hP5ZBeiVTqsnQZADrEHAR8zqESGtZAtn2EXWxZBI3QZDZD"
PHONE_NUMBER_ID = "1097018736835171"
VERIFY_TOKEN = "bot_adawat_manziliya_2026"

RESPONSES = {
    "1": "🏠 *المنتجات والأسعار:*\n\nنوفر تشكيلة واسعة من الأدوات المنزلية:\n\n🔴 *فرامة الضغطة الذكية (المائدة MD-5266):*\n- شفرات فولاذية ضد الصدأ\n- قوة إضافية لتوفير الوقت 60%\n- سهلة الاستخدام\n- السعر: 2,800 ريال\n\n🍲 *طقم قدور المائدة 4 قطع - هندي:*\n- ستانلس ثقيل + أغطية استيل\n- 4 مقاسات: كبير/وسط/صغير/صغير جداً\n- ضمان المائدة\n- الكبير 3,500 | الوسط 3,000 | الصغير 2,500 | الصغير جداً 2,000\n- 🎁 الطقم كامل: 10,500 ريال (وفر 1,000)\n\n☕ *ثلاجة شاي المائدة M213 - 0.7 لتر:*\n- تحفظ الحرارة 6 ساعات\n- الألوان: وردي | بيج | أزرق | كحلي\n- تصميم أنيق للضيافة\n- السعر: 2,500 ريال\n\n📦 التوصيل مجاني داخل المحافظة!\nللمزيد من المنتجات تواصل معنا.\n\nأرسل *قدور* لتفاصيل طقم القدور\nأرسل *ثلاجة* لتفاصيل ثلاجة الشاي",
    "2": "🛒 *طريقة الطلب:*\nيمكنك الطلب عبر:\n1. إرسال اسم المنتج أو صورته هنا.\n2. تزويدنا بالاسم والعنوان.\n3. اختيار وسيلة الدفع (عند الاستلام أو تحويل).\n\n📦 التوصيل مجاني داخل المحافظة!",
    "3": "🚚 *التوصيل والشحن:*\n- التوصيل داخل محافظة إب: *مجاني* ✅\n- الشحن لباقي المحافظات: 2-4 أيام.",
    "4": "🔄 *سياسة الاستبدال والاسترجاع:*\n- الاستبدال خلال 7 أيام من تاريخ الاستلام.\n- الاسترجاع خلال 3 أيام بشرط أن يكون المنتج بحالته الأصلية.",
    "5": "⏰ *مواعيد العمل:*\nمن السبت إلى الخميس:\n- الفترة الصباحية: 9:00 ص - 12:00 م\n- الفترة المسائية: 4:00 م - 10:00 م\nالجمعة: من 4:00 م - 10:00 م",
    "6": "📍 *الموقع والتواصل:*\n- الموقع: إب، اليمن\n- هاتف: +967 773 595 571\n- واتساب: +967 717 864 522\n\nمحل Titiz لبيع وتوزيع جميع الأدوات المنزلية",
    "قدور": "🍲 *طقم قدور المائدة 4 قطع - هندي*\n\n✅ ستانلس ثقيل + أغطية استيل\n✅ 4 مقاسات: كبير/وسط/صغير/صغير جداً\n✅ ضمان المائدة\n\n💰 *الأسعار:*\nالكبير 3,500 | الوسط 3,000\nالصغير 2,500 | الصغير جداً 2,000\n\n🎁 *الطقم كامل:* 10,500 ريال - وفر 1,000\n🚚 توصيل مجاني لداخل المحافظة\n\nاكتب *اطلب* للطلب",
    "ثلاجة": "☕ *ثلاجة شاي المائدة M213 - 0.7 لتر*\n\n✅ تحفظ الحرارة 6 ساعات\n✅ الألوان: وردي 💗 | بيج 🤎 | أزرق 💙 | كحلي\n✅ تصميم أنيق للضيافة\n\n💰 السعر: 2,500 ريال\n\n🚚 توصيل مجاني لداخل المحافظة\n⏰ الكمية محدودة\n\nاكتب *اطلب* للطلب",
    "اطلب": "🛒 *لإتمام الطلب:*\n\nأرسل لنا:\n1. اسم المنتج اللي تبيه\n2. اسمك الكامل\n3. عنوان التوصيل\n4. رقم تواصل آخر (اختياري)\n\n💳 الدفع عند الاستلام\n📦 التوصيل مجاني داخل المحافظة!\n\nوسيتم التواصل معك لتأكيد الطلب ✅",
}

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
            if msg_body in RESPONSES:
                reply = RESPONSES[msg_body]
            else:
                reply = WELCOME_MESSAGE
            send_message(sender, reply)
    except (KeyError, IndexError):
        pass
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "✅ بوت Titiz للأدوات المنزلية يعمل بنجاح!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
