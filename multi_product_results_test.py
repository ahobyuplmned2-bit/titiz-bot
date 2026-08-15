import app


products = [
    {
        "id": 920,
        "name": "قلاص شاي ستيل",
        "price": "1400",
        "quantity": 10,
        "variants": [],
    },
    {
        "id": 921,
        "name": "قلاص شاي زجاج",
        "price": "1600",
        "quantity": 10,
        "variants": [],
    },
]

lists = []
cards = []
messages = []
carousels = []
sender = "967700000000"

app.matching_send_guard.clear()
app.user_sessions.clear()
app.user_states.clear()
app.canonicalize_product = lambda product: product
app.send_list = lambda recipient, text, button_text, sections: lists.append(
    (recipient, text, button_text, sections)
) or True
app.send_carousel = lambda *args, **kwargs: carousels.append(args) or True
app.get_product = lambda product_id: next((item for item in products if item["id"] == int(product_id)), None)
app.send_product_card = lambda recipient, product: cards.append((recipient, product["id"])) or True
app.send_message = lambda recipient, text: messages.append((recipient, text)) or True
app.cancel_customer_followup = lambda recipient: None

assert app.send_matching_products_carousel(sender, products, "قلاصات") is True
assert carousels == []
assert len(lists) == 1
rows = lists[0][3][0]["rows"]
assert [row["id"] for row in rows] == ["product_920", "product_921"]
assert app.user_states[sender] == "search_results"

app.handle_customer_message(sender, "product_921", "product_921", {"type": "interactive"})
assert cards == [(sender, 921)]
assert messages == []

print("multi_product_results_test: OK")
