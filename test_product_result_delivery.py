import app


class FakeWhatsApp:
    def __init__(self, events):
        self.events = events

    def send_url_button(self, to, text, title, url):
        self.events.append(("delegate", to, text, title, url))
        return True


def run():
    events = []
    app.matching_send_guard.clear()
    app.product_send_guard.clear()
    app.user_sessions.clear()
    app.user_states.clear()

    products = [
        {
            "id": 701,
            "name": "مشنات استيل عصاير",
            "price": "1000",
            "description": "مشنات استيل بعصا",
            "keywords": "مشنات استيل,مشنات عصاير",
            "image_urls": '["https://example.test/strainers.png"]',
            "variants": '[{"name":"رقم 1 الكبير","price":1000},{"name":"رقم 2 الوسط","price":800},{"name":"رقم 3 الصغير","price":700}]',
        },
        {
            "id": 702,
            "name": "مشنات عصاير أصلية بطن واحد",
            "price": "500",
            "description": "مشن عصير استيل",
            "keywords": "مشنات,مشن عصير",
            "image_urls": '["https://example.test/single.png"]',
            "variants": "",
        },
    ]

    original_send_message = app.send_message
    original_send_card = app.send_product_card
    original_send_carousel = app.send_carousel
    original_schedule = app.schedule_product_followup
    original_whatsapp = app.whatsapp
    try:
        app.send_message = lambda to, text: events.append(("message", to, text)) or True
        app.send_product_card = lambda to, product: events.append(("card", to, product["name"])) or True
        app.send_carousel = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("لا يجب استخدام الكاروسيل في نتائج البحث")
        )
        app.schedule_product_followup = lambda *args, **kwargs: None
        app.whatsapp = FakeWhatsApp(events)

        sent = app.send_matching_products_carousel("967700000001", products, "مشنات")
        assert sent is True
        assert [item[0] for item in events].count("card") == 2
        assert [item[0] for item in events].count("delegate") == 1
        assert not any(item[0] == "carousel" for item in events)

        events.clear()
        app.get_all_products = lambda: [products[0]]
        app.restore_customer_session = lambda sender: None
        app.cancel_customer_followup = lambda sender: None
        app.interpret_customer_message = lambda sender, body: (_ for _ in ()).throw(
            AssertionError("البحث المطابق لا ينبغي أن يستدعي الذكاء قبل العرض")
        )
        app.handle_customer_message(
            "967700000002",
            "اقلاص استيل",
            app.normalize_text("اقلاص استيل"),
            {"id": "customer-search-test"},
        )
        assert [item[0] for item in events].count("card") == 1
    finally:
        app.send_message = original_send_message
        app.send_product_card = original_send_card
        app.send_carousel = original_send_carousel
        app.schedule_product_followup = original_schedule
        app.whatsapp = original_whatsapp


if __name__ == "__main__":
    run()
    print("product result delivery test passed")
