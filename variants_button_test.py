import app


product = {
    "id": 901,
    "name": "منتج اختبار الحجم",
    "price": "2500",
    "description": "اختبار",
    "quantity": 100,
    "variants": [
        {"name": "1 لتر", "price": "2500"},
        {"name": "2 لتر", "price": "4000"},
    ],
}

sent_lists = []
sent_messages = []
app.get_product = lambda product_id: product if int(product_id) == 901 else None
app.send_variant_list = lambda recipient, selected_product: sent_lists.append((recipient, selected_product["id"]))
app.send_message = lambda recipient, message: sent_messages.append((recipient, message))
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message("967700000000", "variants_901", "variants_901", {"type": "interactive"})
assert sent_lists == [("967700000000", 901)]
assert not sent_messages

sent_lists.clear()
app.variant_button_context["967700000000"] = {
    "product_id": 901,
    "expires_at": app.time.time() + 900,
}
app.handle_customer_message("967700000000", "اختيار الحجم", "اختيار الحجم", {"type": "interactive"})
assert sent_lists == [("967700000000", 901)]
assert not sent_messages

sent_lists.clear()
app.handle_customer_message("967700000000", "📏 اختيار الحجم", "اختيار الحجم", {"type": "interactive"})
assert sent_lists == [("967700000000", 901)]
assert not sent_messages
print("variants_button_test: OK")
