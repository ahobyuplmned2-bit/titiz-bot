"""
مساعد WhatsApp API
يوفر دوال مساعدة للتعامل مع WhatsApp Cloud API
"""

import requests
import time
import json
import re


def parse_product_price(value):
    """استخراج سعر موجب من القيم النصية أو الرقمية بشكل آمن."""
    if isinstance(value, bool):
        return None
    text = str(value or "").replace(",", "").replace("٬", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        price = float(match.group(0))
    except ValueError:
        return None
    return price if price > 0 else None

class WhatsAppAPI:
    """فئة للتعامل مع WhatsApp API"""
    
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/v26.0/{phone_number_id}"
        self.messages_url = f"{self.api_url}/messages"
    
    def send_message(self, recipient_phone, message_text):
        """إرسال رسالة نصية"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "text",
                "text": {
                    "body": message_text
                }
            }
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الرسالة: {e}")
            return False
    
    def mark_as_read(self, message_id):
        """تحديد الرسالة كمقروءة"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في تحديد الرسالة كمقروءة: {e}")
            return False
    
    def send_typing_indicator(self, message_id):
        """إرسال مؤشر الكتابة (جاري الكتابة)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {
                    "type": "text"
                }
            }
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال مؤشر الكتابة: {e}")
            return False
    
    def send_image(self, recipient_phone, image_url, caption=""):
        """إرسال صورة"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "image",
                "image": {
                    "link": image_url
                }
            }
            
            if caption:
                payload["image"]["caption"] = caption
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الصورة: {e}")
            return False
    
    def send_image_by_id(self, recipient_phone, media_id, caption=""):
        """إرسال صورة بمعرف الوسائط"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "image",
                "image": {"id": media_id}
            }
            if caption:
                payload["image"]["caption"] = caption
            response = requests.post(self.messages_url, headers=headers, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الصورة: {e}")
            return False

    def send_audio(self, recipient_phone, audio_bytes, mime_type="audio/mpeg", filename="titiz-reply.mp3"):
        """رفع مقطع صوتي ثم إرساله للعميل كرسالة صوتية عبر WhatsApp Cloud API."""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            upload_response = requests.post(
                f"{self.api_url}/media",
                headers=headers,
                data={"messaging_product": "whatsapp", "type": "audio"},
                files={"file": (filename, audio_bytes, mime_type)},
                timeout=30,
            )
            if upload_response.status_code not in {200, 201}:
                print(f"خطأ رفع الصوت لواتساب: {upload_response.status_code} {upload_response.text[:300]}")
                return False
            media_id = (upload_response.json() or {}).get("id", "")
            if not media_id:
                print("خطأ رفع الصوت لواتساب: لم يرجع معرف الوسائط")
                return False
            response = requests.post(
                self.messages_url,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": recipient_phone,
                    "type": "audio",
                    "audio": {"id": media_id},
                },
                timeout=20,
            )
            if response.status_code != 200:
                print(f"خطأ إرسال الصوت لواتساب: {response.status_code} {response.text[:300]}")
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الصوت: {e}")
            return False

    def send_carousel(self, recipient_phone, message_text, cards):
        """إرسال كاروسيل أفقي من 2 إلى 10 بطاقات صور مع أزرار سريعة."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            carousel_cards = []
            for index, card in enumerate(cards[:10]):
                buttons = []
                for button in card.get("buttons", [])[:2]:
                    buttons.append({
                        "type": "quick_reply",
                        "quick_reply": {
                            "id": str(button.get("id", ""))[:256],
                            "title": str(button.get("title", "اختيار"))[:20],
                        },
                    })
                carousel_cards.append({
                    "card_index": index,
                    "type": "cta_url",
                    "header": {
                        "type": "image",
                        "image": {"link": card["image_url"]},
                    },
                    "body": {"text": card.get("body", "")[:160]},
                    "action": {"buttons": buttons},
                })
            if len(carousel_cards) < 2:
                return False
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient_phone,
                "type": "interactive",
                "interactive": {
                    "type": "carousel",
                    "body": {"text": message_text[:1024]},
                    "action": {"cards": carousel_cards},
                },
            }
            response = requests.post(self.messages_url, headers=headers, json=payload, timeout=15)
            if response.status_code != 200:
                print(f"خطأ كاروسيل واتساب: {response.status_code} {response.text[:300]}")
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الكاروسيل: {e}")
            return False

    def send_buttons(self, recipient_phone, message_text, buttons):
        """إرسال رسالة مع أزرار"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            button_objects = []
            for idx, button in enumerate(buttons[:3], 1):  # الحد الأقصى 3 أزرار
                if isinstance(button, dict):
                    button_id = str(button.get("id") or idx)
                    button_title = str(button.get("title") or "اختيار")
                else:
                    button_id = str(idx)
                    button_title = str(button)
                button_objects.append({
                    "type": "reply",
                    "reply": {
                        "id": button_id[:256],
                        "title": button_title[:20]
                    }
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": message_text
                    },
                    "action": {
                        "buttons": button_objects
                    }
                }
            }
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال الأزرار: {e}")
            return False

    def send_url_button(self, recipient_phone, message_text, button_title, url):
        """إرسال زر CTA يفتح رابطاً خارجياً مثل محادثة واتساب للمندوبة."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "interactive",
                "interactive": {
                    "type": "cta_url",
                    "body": {"text": message_text},
                    "action": {
                        "name": "cta_url",
                        "parameters": {
                            "display_text": str(button_title)[:20],
                            "url": str(url),
                        },
                    },
                },
            }
            response = requests.post(self.messages_url, headers=headers, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"خطأ زر الرابط: {response.status_code} {response.text[:300]}")
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال زر الرابط: {e}")
            return False
    
    def send_list(self, recipient_phone, message_text, button_text="اختر", sections=None):
        """إرسال قائمة تفاعلية"""
        try:
            # دعم الاستدعاء القديم send_list(phone, text, sections)
            if sections is None and isinstance(button_text, list):
                sections = button_text
                button_text = "اختر"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": message_text
                    },
                    "action": {
                        "button": button_text[:20],
                        "sections": sections
                    }
                }
            }
            
            response = requests.post(
                self.messages_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في إرسال القائمة: {e}")
            return False
    
    def send_with_delay(self, recipient_phone, message_text, message_id=None, delay=2):
        """إرسال رسالة مع تأخير (لمحاكاة الكتابة)"""
        # إرسال مؤشر الكتابة
        if message_id:
            self.send_typing_indicator(message_id)
        
        # الانتظار
        time.sleep(delay)
        
        # إرسال الرسالة
        return self.send_message(recipient_phone, message_text)

def create_carousel_message(products):
    """إنشاء رسالة كاروسيل للمنتجات"""
    
    sections = []
    
    for product in products:
        section = {
            "title": "المنتجات",
            "rows": []
        }
        
        for product in products:
            row = {
                "id": str(product.get('id', '')),
                "title": product.get('name', '')[:24],  # الحد الأقصى 24 حرف
                "description": product.get('description', '')[:72]  # الحد الأقصى 72 حرف
            }
            section["rows"].append(row)
        
        sections.append(section)
        break  # قسم واحد فقط
    
    return sections

def format_product_card(product, compact=False):
    """تنسيق بطاقة المنتج، مع نسخة مختصرة للكاروسيل تحفظ السعر دائماً."""

    name = str(product.get("name", "منتج"))
    variants = product.get("variants", "")
    if isinstance(variants, str) and variants.startswith("["):
        try:
            variants = json.loads(variants)
        except json.JSONDecodeError:
            variants = []

    price_lines = []
    if isinstance(variants, list) and variants:
        valid_variants = []
        for variant in variants:
            price = parse_product_price(variant.get("price"))
            if price is not None:
                valid_variants.append((variant, price))
        if valid_variants:
            if compact:
                price_lines.append(
                    "💰 " + " | ".join(
                        f"{variant.get('name') or variant.get('label') or 'الخيار'}: {int(price)}"
                        for variant, price in valid_variants
                    ) + " ريال"
                )
            else:
                price_lines.append("💰 *الأسعار حسب الحجم:*")
                price_lines.extend(
                    f"• {variant.get('name') or variant.get('label') or 'الخيار'}: {int(price)} ريال"
                    for variant, price in valid_variants
                )
        else:
            price_lines.append("💰 السعر: غير محدد حالياً")
    else:
        price = parse_product_price(product.get("price"))
        price_lines.append(f"💰 السعر: {int(price)} ريال" if price is not None else "💰 السعر: غير محدد حالياً")

    availability = "✅ المنتج متوفر" if product.get("quantity", 0) > 0 else "❌ المنتج غير متوفر حالياً"
    description = str(product.get("description") or "").strip()

    if compact:
        # السعر يأتي قبل الوصف، والوصف يُضاف فقط إذا بقي مجال داخل حد WhatsApp للبطاقة.
        message = "\n\n".join([f"📦 *{name}*", "\n".join(price_lines), availability])
        if description:
            short_description = " ".join(description.split())[:55].rstrip()
            candidate = f"{message}\n\n{short_description}"
            if len(candidate) <= 155:
                message = candidate
        return message

    message = f"📦 *{name}*\n\n"
    if description:
        message += f"{description}\n\n"
    message += "\n".join(price_lines) + f"\n\n{availability}\n"
    message += f"\nاختاري الزر المناسب من الأسفل 👇\nأو اكتبي: اضف {name}"
    return message
