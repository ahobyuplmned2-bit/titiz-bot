import app


product = {
    "id": 902,
    "name": "كتلي شاي اختبار",
    "price": "2500",
    "description": "تفاصيل المنتج الاختبارية",
    "quantity": 10,
    "variants": [
        {"name": "1 لتر", "price": "2500"},
        {"name": "2 لتر", "price": "3500"},
    ],
}

sent_lists = []
sent_messages = []
sent_buttons = []
events = []
app.get_product = lambda product_id: product if int(product_id) == 902 else None
app.send_variant_list = lambda recipient, selected_product: sent_lists.append((recipient, selected_product["id"]))
app.send_message = lambda recipient, text: sent_messages.append((recipient, text))
app.send_buttons = lambda recipient, text, buttons: sent_buttons.append((recipient, text, buttons))
app.send_cart_view = lambda recipient: events.append(("cart", recipient))
app.send_customer_orders = lambda recipient: events.append(("orders", recipient))
app.send_offers_response = lambda recipient: events.append(("offers", recipient))
app.send_contact_menu = lambda recipient: events.append(("contact", recipient))
app.send_product_request_menu = lambda recipient: events.append(("assistant", recipient))
app.cancel_customer_followup = lambda recipient: None
app.schedule_product_followup = lambda *args, **kwargs: None
app.user_states["967700000000"] = "product_context"
app.user_sessions["967700000000"] = {"last_product": product}
app.variant_button_context["967700000000"] = {
    "product_id": 902,
    "expires_at": app.time.time() + 900,
}

app.handle_customer_message("967700000000", "📏 اختيار الحجم", "اختيار الحجم", {"type": "interactive"})
assert sent_lists == [("967700000000", 902)]
assert not sent_messages

sent_lists.clear()
app.handle_customer_message("967700000000", "🛒 إضافة للسلة", "اضافة للسلة", {"type": "text"})
assert sent_lists == [("967700000000", 902)]
assert not sent_messages

sent_lists.clear()
app.handle_customer_message("967700000000", "📋 التفاصيل", "التفاصيل", {"type": "text"})
assert any("تفاصيل المنتج" in text for _, text in sent_messages)
assert sent_buttons

sent_messages.clear()
app.handle_customer_message("967700000000", "🛍️ عرض السلة", "عرض السلة", {"type": "text"})
app.handle_customer_message("967700000000", "📦 طلباتي", "طلباتي", {"type": "text"})
app.handle_customer_message("967700000000", "🎁 العروض", "العروض", {"type": "text"})
app.handle_customer_message("967700000000", "📞 التواصل مع المندوبة", "التواصل مع المندوبة", {"type": "text"})
assert events == [
    ("cart", "967700000000"),
    ("orders", "967700000000"),
    ("offers", "967700000000"),
    ("contact", "967700000000"),
]

print("button_text_alias_test: OK")
