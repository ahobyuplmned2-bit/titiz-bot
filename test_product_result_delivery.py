import app
import whatsapp_api


class FakeWhatsApp:
    def __init__(self, events):
        self.events = events

    def send_url_button(self, to, text, title, url):
        self.events.append(("delegate", to, text, title, url))
        return True


def sample_products():
    return [
        {
            "id": 701,
            "name": "مشنات استيل عصاير",
            "price": "1000",
            "description": "مشنات استيل بعصا",
            "keywords": "مشنات استيل,مشنات عصاير",
            "image_urls": '["https://example.test/strainers.jpg"]',
            "variants": '[{"name":"رقم 1 الكبير","price":1000},{"name":"رقم 2 الوسط","price":800},{"name":"رقم 3 الصغير","price":700}]',
        },
        {
            "id": 702,
            "name": "مشنات عصاير أصلية بطن واحد",
            "price": "500",
            "description": "مشن عصير استيل",
            "keywords": "مشنات,مشن عصير",
            "image_urls": '["https://example.test/single.jpg"]',
            "variants": "",
        },
    ]


def test_search_result_uses_carousel():
    events = []
    products = sample_products()
    original_send_message = app.send_message
    original_send_card = app.send_product_card
    original_send_carousel = app.send_carousel
    original_schedule = app.schedule_product_followup
    original_whatsapp = app.whatsapp
    try:
        app.matching_send_guard.clear()
        app.send_message = lambda to, text: events.append(("message", to, text)) or True
        app.send_product_card = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("لا يجب إرسال البطاقات الفردية عندما ينجح الكاروسيل")
        )

        def fake_carousel(to, text, cards):
            events.append(("carousel", to, text, cards))
            assert len(cards) == 2
            assert all(card["image_url"].startswith("https://") for card in cards)
            assert {len(card["buttons"]) for card in cards} == {2}
            assert all(
                button["id"].startswith(("variants_", "add_", "det_"))
                for card in cards
                for button in card["buttons"]
            )
            return True

        app.send_carousel = fake_carousel
        app.schedule_product_followup = lambda *args, **kwargs: None
        app.whatsapp = FakeWhatsApp(events)
        assert app.send_matching_products_carousel("967700000001", products, "مشنات") is True
        assert [item[0] for item in events].count("carousel") == 1
        assert [item[0] for item in events].count("delegate") == 1
    finally:
        app.send_message = original_send_message
        app.send_product_card = original_send_card
        app.send_carousel = original_send_carousel
        app.schedule_product_followup = original_schedule
        app.whatsapp = original_whatsapp


def test_search_result_falls_back_only_when_carousel_fails():
    events = []
    products = sample_products()
    original_send_message = app.send_message
    original_send_card = app.send_product_card
    original_send_carousel = app.send_carousel
    original_schedule = app.schedule_product_followup
    original_whatsapp = app.whatsapp
    try:
        app.matching_send_guard.clear()
        app.send_message = lambda to, text: events.append(("message", to, text)) or True
        app.send_carousel = lambda *args, **kwargs: False
        app.send_product_card = lambda to, product: events.append(("card", to, product["name"])) or True
        app.schedule_product_followup = lambda *args, **kwargs: None
        app.whatsapp = FakeWhatsApp(events)
        assert app.send_matching_products_carousel("967700000002", products, "مشنات") is True
        assert [item[0] for item in events].count("card") == 2
        assert [item[0] for item in events].count("delegate") == 1
    finally:
        app.send_message = original_send_message
        app.send_product_card = original_send_card
        app.send_carousel = original_send_carousel
        app.schedule_product_followup = original_schedule
        app.whatsapp = original_whatsapp


def test_whatsapp_carousel_payload_shape():
    events = []
    original_post = whatsapp_api.requests.post
    original_sleep = whatsapp_api.time.sleep

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"messages": [{"id": "wamid.test"}]}

    def fake_post(url, headers, json, timeout):
        events.append(json)
        return FakeResponse()

    try:
        whatsapp_api.requests.post = fake_post
        whatsapp_api.time.sleep = lambda seconds: None
        client = whatsapp_api.WhatsAppAPI("token", "phone-id")
        assert client.send_carousel(
            "967700000003",
            "منتجات مشابهة",
            [
                {"image_url": "https://example.test/a.jpg", "body": "A", "buttons": [{"id": "a1", "title": "اختيار"}, {"id": "a2", "title": "تفاصيل"}]},
                {"image_url": "https://example.test/b.jpg", "body": "B", "buttons": [{"id": "b1", "title": "اختيار"}, {"id": "b2", "title": "تفاصيل"}]},
            ],
        )
        payload = events[0]
        cards = payload["interactive"]["action"]["cards"]
        assert payload["interactive"]["type"] == "carousel"
        assert cards[0]["header"]["image"]["link"].endswith("a.jpg")
        assert all(card["action"]["buttons"][0]["type"] == "quick_reply" for card in cards)
        assert all(len(card["action"]["buttons"]) == 2 for card in cards)
    finally:
        whatsapp_api.requests.post = original_post
        whatsapp_api.time.sleep = original_sleep


def test_admin_order_buttons_regression():
    events = []
    original_send_message = app.send_message
    original_get_order = app.get_order
    original_update_status = app.update_order_status
    try:
        app.send_message = lambda to, text: events.append(("message", to, text)) or True
        app.get_order = lambda num: {"order_number": num, "phone_number": "967700009999"} if num == "ORD-00003" else None
        updated_statuses = []
        app.update_order_status = lambda num, status: updated_statuses.append((num, status))

        owner_phone = app.OWNER_NUMBER
        app.handle_owner_command(owner_phone, "admin_prep_ORD-00003", "admin_prep_ORD-00003", {"type": "text"})

        assert not any("لم أتمكن من معرفة رقم العميل" in text for _, _, text in events if _ == "message")
        assert ("ORD-00003", "جاري التجهيز") in updated_statuses
        assert ("967700009999", "📦 *تحديث لطلبك ORD-00003*\n\n✅ جاري تجهيز طلبك الآن وسيتم إرساله قريباً بشغف وسعادة 😊") in [(to, text) for _, to, text in events]

        # حماية: بعض أزرار الإدارة تصل ومعها context مقتبس من إشعار الطلب.
        # يجب أن يأخذ المعرّف admin_deliv_ الأولوية ولا يطلب رقم العميل.
        events.clear()
        updated_statuses.clear()
        quoted_button_message = {
            "type": "interactive",
            "context": {"id": "wamid.fake-order-card", "text": "طلب جديد بدون رقم ظاهر"},
        }
        app.handle_owner_command(owner_phone, "admin_deliv_ORD-00003", "admin_deliv_ORD-00003", quoted_button_message)

        assert not any("لم أتمكن من معرفة رقم العميل" in text for kind, _, text in events if kind == "message")
        assert ("ORD-00003", "تم التسليم") in updated_statuses
        assert any(to == "967700009999" and "تم تسليم طلبك بنجاح" in text for kind, to, text in events if kind == "message")
    finally:
        app.send_message = original_send_message
        app.get_order = original_get_order
        app.update_order_status = original_update_status


if __name__ == "__main__":
    test_search_result_uses_carousel()
    test_search_result_falls_back_only_when_carousel_fails()
    test_whatsapp_carousel_payload_shape()
    test_admin_order_buttons_regression()
    print("all product result delivery and admin buttons tests passed")



def test_customer_image_flow_regression():
    events = []
    original_analyze = app.analyze_product_image
    original_notify = app.notify_owner_unavailable_product
    original_send_unavailable = app.send_unavailable_image_response
    original_send_card = app.send_product_card
    try:
        original_send_msg = app.send_message
        original_send_img = app.send_image_by_id
        app.send_message = lambda to, text: events.append(("message", to, text)) or True
        app.send_image_by_id = lambda to, media_id, caption: events.append(("send_image", to, media_id)) or True
        app.send_unavailable_image_response = lambda to: events.append(("unavailable_response", to)) or app.send_message(to, app.UNAVAILABLE_IMAGE_RESPONSE)
        app.send_product_card = lambda to, prod: events.append(("product_card", to, prod.get("name")))

        # حالة 1: صورة منتج غير موجود ترسل تنبيه الإدارة ورسالة التأكيد للعميل
        app.processed_messages.clear()
        app.analyze_product_image = lambda sender, msg, cap: {"kind": "unknown", "reply": "غير متوفر"}
        original_match = app.match_products_from_text
        app.match_products_from_text = lambda cap, prods: []
        msg = {"type": "image", "image": {"id": "img_123", "caption": "منتج وهمي غير موجود"}}
        app.handle_customer_message("967700001111", "", "", msg)
        app.match_products_from_text = original_match

        assert any(e[0] == "message" for e in events)
        assert any(e[0] == "unavailable_response" and e[1] == "967700001111" for e in events)

        # حالة 2: صورة منتج موجود ترسل بطاقة أو كاروسيل المطابق
        events.clear()
        app.processed_messages.clear()
        sample_prod = {"id": 999, "name": "برش رضاعات كبير", "price": "500", "image_urls": '["https://example.test/img.jpg"]'}
        original_related = app.products_related_to_image
        app.products_related_to_image = lambda prod, all_prods: [prod]
        app.analyze_product_image = lambda sender, msg, cap: {"kind": "product", "product": sample_prod, "variant_match": None}
        app.handle_customer_message("967700002222", "", "", msg)

        assert any(e[0] == "product_card" and e[2] == "برش رضاعات كبير" for e in events)
        app.products_related_to_image = original_related
    finally:
        app.analyze_product_image = original_analyze
        app.notify_owner_unavailable_product = original_notify
        app.send_unavailable_image_response = original_send_unavailable
        app.send_product_card = original_send_card
        app.send_message = original_send_msg
        app.send_image_by_id = original_send_img


if __name__ == "__main__":
    test_search_result_uses_carousel()
    test_search_result_falls_back_only_when_carousel_fails()
    test_whatsapp_carousel_payload_shape()
    test_admin_order_buttons_regression()
    test_customer_image_flow_regression()
    print("all product result delivery, admin buttons, and image flow tests passed")
