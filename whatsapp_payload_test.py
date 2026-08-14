import whatsapp_api


requests_payloads = []


class FakeResponse:
    status_code = 200
    text = "ok"


def fake_post(url, **kwargs):
    requests_payloads.append((url, kwargs.get("json") or {}))
    return FakeResponse()


whatsapp_api.requests.post = fake_post
client = whatsapp_api.WhatsAppAPI("test-token", "test-phone-id")

assert client.send_message("967700000001", "رسالة اختبار")
assert client.send_image("967700000001", "https://example.com/product.jpg", "صورة")
assert client.send_image_by_id("967700000001", "media-id", "صورة")
assert client.send_buttons("967700000001", "اختاري", [
    {"id": "a", "title": "أول"},
    {"id": "b", "title": "ثاني"},
    {"id": "c", "title": "ثالث"},
    {"id": "d", "title": "رابع"},
])
assert client.send_list("967700000001", "الخدمات", "اختاري", [{
    "title": "القائمة",
    "rows": [{"id": "menu_search", "title": "بحث", "description": "بحث عن منتج"}],
}])
assert client.send_url_button("967700000001", "مساعدة", "مراسلة", "https://wa.me/967712282204")

buttons_payload = requests_payloads[3][1]
assert buttons_payload["interactive"]["type"] == "button"
assert len(buttons_payload["interactive"]["action"]["buttons"]) == 3
assert requests_payloads[4][1]["interactive"]["type"] == "list"
assert requests_payloads[5][1]["interactive"]["type"] == "cta_url"

print("whatsapp_payload_test: OK")
