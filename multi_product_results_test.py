import app


products = [
    {
        "id": 920,
        "name": "قلاص شاي ستيل",
        "price": "1400",
        "quantity": 10,
        "variants": [],
        "image_urls": '["https://catalog.test/glass-steel.jpg"]',
    },
    {
        "id": 921,
        "name": "قلاص شاي زجاج",
        "price": "1600",
        "quantity": 10,
        "variants": [],
        "image_urls": '["https://catalog.test/glass-glass.jpg"]',
    },
]

carousel_calls = []
cards = []
messages = []
sender = "967700000000"

app.matching_send_guard.clear()
app.user_sessions.clear()
app.user_states.clear()
app.canonicalize_product = lambda product: product
app.send_carousel = lambda recipient, text, carousel_cards: carousel_calls.append(
    (recipient, text, carousel_cards)
) or True
app.get_product = lambda product_id: next((item for item in products if item["id"] == int(product_id)), None)
app.send_product_card = lambda recipient, product: cards.append((recipient, product["id"])) or True
app.send_message = lambda recipient, text: messages.append((recipient, text)) or True
app.cancel_customer_followup = lambda recipient: None

assert app.send_matching_products_carousel(sender, products, "قلاصات") is True
assert len(carousel_calls) == 1
carousel_cards = carousel_calls[0][2]
assert len(carousel_cards) == 2
assert carousel_cards[0]["buttons"][0]["id"] == "add_920"
assert carousel_cards[1]["buttons"][0]["id"] == "add_921"
assert app.user_states[sender] == "product_context"
assert app.user_sessions[sender]["last_product"]["id"] == 920
assert cards == []
assert messages == []

print("multi_product_results_test: OK")
