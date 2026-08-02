"""
مساعد WhatsApp API
يوفر دوال مساعدة للتعامل مع WhatsApp Cloud API
"""

import requests
import time
import json

class WhatsAppAPI:
    """فئة للتعامل مع WhatsApp API"""
    
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
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
    
    def send_typing_indicator(self, recipient_phone):
        """إرسال مؤشر الكتابة"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient_phone,
                "type": "typing"
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

    def send_buttons(self, recipient_phone, message_text, buttons):
        """إرسال رسالة مع أزرار"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            button_objects = []
            for idx, button_text in enumerate(buttons[:3], 1):  # الحد الأقصى 3 أزرار
                button_objects.append({
                    "type": "reply",
                    "reply": {
                        "id": str(idx),
                        "title": button_text
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
    
    def send_list(self, recipient_phone, message_text, sections):
        """إرسال قائمة تفاعلية"""
        try:
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
                        "button": "اختر",
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
    
    def send_with_delay(self, recipient_phone, message_text, delay=2):
        """إرسال رسالة مع تأخير (لمحاكاة الكتابة)"""
        # إرسال مؤشر الكتابة
        self.send_typing_indicator(recipient_phone)
        
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

def format_product_card(product):
    """تنسيق بطاقة المنتج"""
    
    message = f"📦 *{product.get('name', 'منتج')}*\n\n"
    
    if product.get('description'):
        message += f"{product['description']}\n\n"
    
    message += f"💰 السعر: {product.get('price', 0)} ريال\n"
    
    if product.get('quantity', 0) > 0:
        message += f"✅ المنتج متوفر\n"
    else:
        message += f"❌ المنتج غير متوفر حالياً\n"
    
    message += f"\n🛒 اكتبي *اضف* لإضافة المنتج إلى السلة"
    
    return message
