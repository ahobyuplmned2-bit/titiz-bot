import app


products = [
    {
        "id": 42,
        "name": "عصارة الدار بلاستيك مدورة أصلية",
        "keywords": "عصارة,عصارات,عصارات بلاستيك",
    }
]

matched = app.resolve_image_product_match(
    {
        "matched_product_id": None,
        "matched_product_name": "عصارة الدار بلاستيك مدورة أصلية",
        "confidence": 0.42,
        "reply": "هذه صورة عصارة الدار",
    },
    products,
)
assert matched and matched["id"] == 42

assert app.resolve_image_product_match(
    {"matched_product_id": 42, "confidence": 0.61, "matched_product_name": ""},
    products,
)["id"] == 42

assert app.resolve_image_product_match(
    {
        "matched_product_id": None,
        "matched_product_name": "عصارة الدار بلاستيك مدورة",
        "confidence": 0.38,
        "reply": "",
    },
    products,
)["id"] == 42

uncertain = []
unavailable = []
sent = []
app.analyze_product_image = lambda *args, **kwargs: {"kind": "unknown", "reply": "غير واضح"}
app.notify_owner_uncertain_product_image = lambda *args, **kwargs: uncertain.append(args)
app.notify_owner_unavailable_product = lambda *args, **kwargs: unavailable.append(args)
app.send_message = lambda recipient, text: sent.append((recipient, text))
app.send_image_by_id = lambda *args, **kwargs: None
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message(
    "967700000000",
    "",
    "",
    {"type": "image", "image": {"id": "media-123", "caption": ""}, "context": {"forwarded": True}},
)

assert uncertain
assert unavailable == []
assert sent == []

tea_products = [
    {"id": 51, "name": "ثلاجة شاي المائدة", "keywords": "ثلاجة,ثلاجات,شاي"},
    {"id": 52, "name": "ثلاجات شاي التاج الملكي", "keywords": "ثلاجة,ثلاجات,شاي,التاج"},
]
assert {item["id"] for item in app.products_related_to_image(tea_products[0], tea_products)} == {51, 52}

sent_cards = []
cart_additions = []
button_messages = []
app.analyze_product_image = lambda *args, **kwargs: {"kind": "product", "product": products[0]}
app.get_all_products = lambda: products
real_send_product_card = app.send_product_card
app.send_product_card = lambda recipient, product: (
    sent_cards.append((recipient, product)),
    real_send_product_card(recipient, product),
)[1]
app.add_to_cart = lambda recipient, product_id, quantity: cart_additions.append(
    (recipient, product_id, quantity)
) or True
app.send_buttons = lambda recipient, text, buttons: button_messages.append((recipient, text, buttons))

app.handle_customer_message(
    "967700000000",
    "",
    "",
    {"type": "image", "image": {"id": "media-456", "caption": ""}},
)
assert sent_cards
assert app.user_states["967700000000"] == "product_context"

app.handle_customer_message(
    "967700000000",
    "أشتي هاذا",
    app.normalize_text("أشتي هاذا"),
    {"type": "text"},
)
assert cart_additions == [("967700000000", 42, 1)]
assert any(button["id"] == "checkout" for button in button_messages[-1][2])
print("image_forwarded_test: OK")
