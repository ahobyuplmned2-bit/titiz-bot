"""
مساعد WhatsApp API
يوفر دوال مساعدة للتعامل مع WhatsApp Cloud API
"""

import requests
import time
import json
import re
import os
from threading import Lock


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


def format_product_card(product):
    """تنسيق بطاقة عرض المنتج"""
    name = product.get("name", "")
    price = product.get("price", 0)
    desc = product.get("description", "")
    return f"☕ *{name}*\n\n{desc}\n\n💰 السعر: {price} ريال"

class WhatsAppAPI:
    """فئة للتعامل مع WhatsApp API"""
    
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/v26.0/{phone_number_id}"
        self.messages_url = f"{self.api_url}/messages"
        self._outbound_lock = Lock()
        self._last_outbound_at = 0.0
        self._cooldown_until = 0.0
        self._min_outbound_interval = max(
            float(os.environ.get("WHATSAPP_SEND_MIN_INTERVAL_SECONDS", "0.45")), 0.1
        )
        self._rate_limit_cooldown = max(
            float(os.environ.get("WHATSAPP_429_COOLDOWN_SECONDS", "8")), 1.0
        )

    def _post_outbound_message(self, headers, payload, timeout=10):
        with self._outbound_lock:
            now = time.monotonic()
            if now < self._cooldown_until:
                return None
            wait_seconds = self._min_outbound_interval - (now - self._last_outbound_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            response = requests.post(self.messages_url, headers=headers, json=payload, timeout=timeout)
            self._last_outbound_at = time.monotonic()
            if response.status_code == 429:
                try:
                    retry_after = float(response.headers.get("Retry-After", "0") or 0)
                except (TypeError, ValueError):
                    retry_after = 0.0
                cooldown = max(retry_after, self._rate_limit_cooldown)
                self._cooldown_until = self._last_outbound_at + cooldown
            return response
    
    def send_message(self, recipient_phone, message_text):
        """إرسال رسالة نصية وتعيد معرف الرسالة (wamid) إذا نجح الإرسال أو True"""
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
            response = self._post_outbound_message(headers, payload, timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                if messages:
                    return messages[0].get("id", True)
                return True
            return False
        except Exception as e:
            print(f"خطأ في إرسال الرسالة: {e}")
            return False
    
    def mark_as_read(self, message_id):
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
            response = requests.post(self.messages_url, headers=headers, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"خطأ في تحديد الرسالة كمقروءة: {e}")
            return False

    def send_typing_indicator(self, message_id):
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "status": "hsm",
                "message_id": message_id
            }
            requests.post(self.messages_url, headers=headers, json=payload, timeout=5)
        except Exception:
            pass
