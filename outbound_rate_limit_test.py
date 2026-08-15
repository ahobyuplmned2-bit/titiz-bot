import whatsapp_api


class Response:
    def __init__(self, status_code, retry_after=None):
        self.status_code = status_code
        self.text = "rate limited" if status_code == 429 else "ok"
        self.headers = {"Retry-After": retry_after} if retry_after else {}


calls = []
sequence = [Response(429, "1"), Response(200)]
original_post = whatsapp_api.requests.post
original_sleep = whatsapp_api.time.sleep


def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
    calls.append((url, json))
    return sequence.pop(0) if sequence else Response(200)


whatsapp_api.requests.post = fake_post
whatsapp_api.time.sleep = lambda seconds: None
try:
    api = whatsapp_api.WhatsAppAPI("token", "phone-id")
    api._rate_limit_cooldown = 1
    assert api.send_message("967700000000", "الرد الأول") is False
    assert len(calls) == 1
    assert api.send_message("967700000000", "رد محجوب") is False
    assert len(calls) == 1
    api._cooldown_until = 0
    assert api.send_buttons("967700000000", "اختاري", [{"id": "x", "title": "زر"}]) is True
    assert len(calls) == 2
finally:
    whatsapp_api.requests.post = original_post
    whatsapp_api.time.sleep = original_sleep

print("outbound_rate_limit_test: OK")
