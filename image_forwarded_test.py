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
assert any("لم أعتبرها غير متوفرة" in text for _, text in sent)
print("image_forwarded_test: OK")
