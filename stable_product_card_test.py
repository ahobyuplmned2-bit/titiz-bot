import app


product = {
    "id": 909,
    "name": "كتلي شاي تجريبي",
    "price": "2700",
    "description": "كتلي ستيل بأحجام متعددة",
    "quantity": 10,
    "image_urls": '["https://catalog.test/kettle-1.jpg", "https://catalog.test/kettle-2.jpg"]',
    "variants": '[{"name": "1 لتر", "price": "2700"}, {"name": "2 لتر", "price": "4000"}]',
}

images = []
messages = []
variant_lists = []
carousel_calls = []

app.product_send_guard.clear()
app.canonicalize_product = lambda selected: selected
app.send_image = lambda recipient, url, caption="": images.append((recipient, url, caption)) or True
app.send_message = lambda recipient, text: messages.append((recipient, text)) or True
app.send_variant_list = lambda recipient, selected: variant_lists.append((recipient, selected["id"])) or True
app.send_carousel = lambda *args, **kwargs: carousel_calls.append(args) or True
app.schedule_product_followup = lambda *args, **kwargs: None

assert app.send_product_card("967700000000", product) is True
assert images == [("967700000000", "https://catalog.test/kettle-1.jpg", "")]
assert len(messages) == 1 and "كتلي شاي تجريبي" in messages[0][1]
assert variant_lists == [("967700000000", 909)]
assert carousel_calls == []

print("stable_product_card_test: OK")
