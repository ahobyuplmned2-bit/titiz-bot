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
    log_action, get_statistics, load_qa, save_qa
)
from cart_system import CartManager, OrderManager, format_cart_message
from payment_system import PaymentManager, format_payment_proof_message
from whatsapp_api import WhatsAppAPI, format_product_card

app = Flask(__name__)

# ===== الإعدادات العامة =====
BOT_NAME = "Titiz موظفتك الذكية نرد على جميع طلباتكم 24 ساعة"
HIDE_ADMIN_NUMBER = True

# ===== بيانات WhatsApp =====
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "").strip()
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "").strip()
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "bot_adawat_manziliya_2026")
OWNER_NUMBER = os.environ.get("OWNER_NUMBER", "967773595571")

# ===== بيانات GitHub =====
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "ahobyuplmned2-bit/titiz-bot"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
PRODUCTS_FILE = "products.json"
QA_FILE = "qa.json"

# ===== تهيئة الخدمات =====
whatsapp = WhatsAppAPI(ACCESS_TOKEN, PHONE_NUMBER_ID)
init_db()

# ===== متغيرات الجلسات =====
user_sessions = {}
user_states = {}  # تتبع حالة المستخدم (في السلة، الدفع، إلخ)

# ===== الرسائل الثابتة =====
WELCOME_MESSAGE = f"""
👋 *أهلاً وسهلاً في {BOT_NAME}*

🛍️ نحن هنا لخدمتك 24 ساعة!

📋 *القائمة الرئيسية:*
1️⃣ تصفح المنتجات
2️⃣ البحث عن منتج
3️⃣ السلة 🛒
4️⃣ طلباتي
5️⃣ طرق الدفع
6️⃣ التواصل معنا

اكتبي رقم الخيار أو اسم ما تبحثين عنه 😊
"""

MAIN_MENU_BUTTONS = [
    "🛍️ تصفح المنتجات",
    "🔍 البحث عن منتج",
    "🛒 السلة"
]

# ===== دوال مساعدة =====

def normalize_text(text):
    """تطبيع النص للبحث"""
    return text.strip().lower()

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
        payload = {
            "message": f"Update {filename}",
            "content": content
        }
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

def send_message(recipient_phone, message_text):
    """إرسال رسالة نصية"""
    return whatsapp.send_message(recipient_phone, message_text)

def send_message_with_delay(recipient_phone, message_text, delay=2):
    """إرسال رسالة مع تأخير"""
    return whatsapp.send_with_delay(recipient_phone, message_text, delay)

def send_image(recipient_phone, image_url, caption=""):
    """إرسال صورة"""
    return whatsapp.send_image(recipient_phone, image_url, caption)

def send_buttons(recipient_phone, message_text, buttons):
    """إرسال أزرار"""
    return whatsapp.send_buttons(recipient_phone, message_text, buttons)

def mark_as_read(message_id):
    """تحديد الرسالة كمقروءة"""
    return whatsapp.mark_as_read(message_id)

def notify_admin(message_text):
    """إرسال إشعار للإدارة"""
    send_message(OWNER_NUMBER, message_text)

# ===== معالجات الأوامر =====

def handle_cart_command(sender):
    """معالجة أمر السلة"""
    cart_summary = CartManager.get_cart_summary(sender)
    message = format_cart_message(cart_summary)
    send_message(sender, message)

def handle_add_to_cart(sender, product_name):
    """معالجة إضافة منتج للسلة"""
    # البحث عن المنتج
    products = get_all_products()
    
    for product in products:
        if normalize_text(product_name) in normalize_text(product['name']):
            CartManager.add_product(sender, product['id'], 1)
            message = f"✅ تم إضافة *{product['name']}* إلى السلة\n\n"
            message += f"💰 السعر: {product['price']} ريال\n"
            message += f"🛒 عدد العناصر في السلة: {len(CartManager.get_cart_items(sender))}\n\n"
            message += "اكتبي *السلة* لعرض السلة الكاملة"
            send_message(sender, message)
            log_action('cart', sender, 'add_product', f'Product: {product["name"]}')
            return
    
    send_message(sender, "❌ لم أجد المنتج المطلوب\n\nاكتبي *تصفح* لعرض جميع المنتجات")

def handle_complete_order(sender):
    """معالجة إكمال الطلب"""
    cart_items = CartManager.get_cart_items(sender)
    
    if not cart_items:
        send_message(sender, "❌ السلة فارغة!\n\nاكتبي *تصفح* لاستعراض المنتجات")
        return
    
    # طلب بيانات العميل
    customer = get_customer(sender)
    
    if customer:
        message = f"👤 *تأكيد البيانات:*\n\n"
        message += f"الاسم: {customer.get('name', 'غير محدد')}\n"
        message += f"الهاتف: {sender}\n"
        message += f"العنوان: {customer.get('address', 'غير محدد')}\n\n"
        message += "اكتبي *تأكيد* لإكمال الطلب أو *تعديل* لتغيير البيانات"
    else:
        message = "📝 يرجى إدخال بيانات التوصيل:\n\n"
        message += "1️⃣ اسمك الكامل\n"
        message += "2️⃣ عنوان التوصيل\n\n"
        message += "أرسلي البيانات بالصيغة: *الاسم | العنوان*"
    
    user_states[sender] = 'waiting_for_order_confirmation'
    send_message(sender, message)

def handle_payment_method(sender):
    """معالجة اختيار طريقة الدفع"""
    message = PaymentManager.get_payment_methods_message()
    user_states[sender] = 'waiting_for_payment_choice'
    send_buttons(sender, message, ["الدفع عند الاستلام", "التحويل المسبق"])

# ===== معالج الرسائل الرئيسي =====

@app.route("/webhook", methods=["POST"])
def webhook():
    """معالج webhook لاستقبال الرسائل"""
    try:
        data = request.get_json()
        
        # التحقق من الرسالة
        if data.get("object") != "whatsapp_business_account":
            return jsonify({"status": "ok"}), 200
        
        # استخراج بيانات الرسالة
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return jsonify({"status": "ok"}), 200
        
        message = messages[0]
        message_id = message.get("id")
        sender = message.get("from")
        message_type = message.get("type", "text")
        
        # تحديد الرسالة كمقروءة
        mark_as_read(message_id)
        
        # إضافة العميل
        add_customer(sender)
        
        # معالجة الرسالة
        if message_type == "text":
            message_text = message.get("text", {}).get("body", "").strip()
            message_normalized = normalize_text(message_text)
            
            # إرسال مؤشر الكتابة
            whatsapp.send_typing_indicator(sender)
            time.sleep(1)
            
            # معالجة الأوامر
            if message_normalized in ["السلة", "عربتي", "الشراء"]:
                handle_cart_command(sender)
            
            elif message_normalized in ["اكمل الطلب", "إكمال الطلب", "شراء"]:
                handle_complete_order(sender)
            
            elif message_normalized in ["الدفع", "طرق الدفع", "دفع"]:
                handle_payment_method(sender)
            
            elif message_normalized in ["تصفح", "منتجات", "البضاعة"]:
                products = get_all_products()
                if products:
                    message = "🛍️ *المنتجات المتاحة:*\n\n"
                    for idx, product in enumerate(products[:10], 1):
                        message += f"{idx}. {product['name']} - {product['price']} ريال\n"
                    message += "\n📝 اكتبي اسم المنتج أو رقمه للمزيد من التفاصيل"
                    send_message(sender, message)
                else:
                    send_message(sender, "❌ لا توجد منتجات متاحة حالياً")
            
            elif message_normalized in ["القائمة", "الرئيسية", "ابدأ"]:
                send_message(sender, WELCOME_MESSAGE)
            
            elif message_normalized in ["اضف", "أضف"]:
                # البحث عن آخر منتج تم البحث عنه
                if sender in user_sessions and user_sessions[sender]:
                    product = user_sessions[sender][0]
                    CartManager.add_product(sender, product['id'], 1)
                    send_message(sender, f"✅ تم إضافة *{product['name']}* إلى السلة")
                else:
                    send_message(sender, "❌ لم أجد منتج لإضافته\n\nاكتبي اسم المنتج أولاً")
            
            else:
                # البحث عن منتج
                products = get_all_products()
                matching = [p for p in products if normalize_text(message_normalized) in normalize_text(p['name'])]
                
                if len(matching) == 1:
                    product = matching[0]
                    message = format_product_card(product)
                    if product.get('image_id'):
                        send_image(sender, product['image_id'], message)
                    else:
                        send_message(sender, message)
                    user_sessions[sender] = [product]
                
                elif len(matching) > 1:
                    message = "🔍 *وجدنا المنتجات التالية:*\n\n"
                    for idx, p in enumerate(matching[:10], 1):
                        message += f"{idx}. {p['name']} - {p['price']} ريال\n"
                    message += "\n📝 اكتبي رقم المنتج أو اسمه الكامل"
                    send_message(sender, message)
                    user_sessions[sender] = matching
                
                else:
                    send_message(sender, f"❌ لم أجد منتج باسم '{message_text}'\n\nاكتبي *تصفح* لعرض جميع المنتجات")
        
        log_action('message', sender, 'received', message_text if message_type == 'text' else message_type)
        
    except Exception as e:
        print(f"خطأ: {e}")
        log_action('error', None, 'webhook_error', str(e))
    
    return jsonify({"status": "ok"}), 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """التحقق من webhook"""
    verify_token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if verify_token == VERIFY_TOKEN:
        return challenge
    
    return "Invalid token", 403

@app.route("/", methods=["GET"])
def home():
    """الصفحة الرئيسية"""
    return f"✅ {BOT_NAME} يعمل بنجاح!", 200

@app.route("/stats", methods=["GET"])
def get_stats():
    """الحصول على الإحصائيات"""
    stats = get_statistics()
    return jsonify(stats), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
