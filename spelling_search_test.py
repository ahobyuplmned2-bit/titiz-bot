import app


products = [
    {
        "id": 1,
        "name": "طقم قدور المائدة هندي",
        "keywords": "قدور,قدور هندية,طقم قدور",
        "description": "ستانلس ثقيل مع أغطية استيل ومقاسات متعددة",
        "price": "10500",
        "image_urls": "[]",
    },
    {
        "id": 2,
        "name": "قطاعة الخضروات",
        "keywords": "قطاعة,قطاعه,تقطيع",
        "description": "تقطع الخضروات بسرعة وسهولة",
        "price": "1500",
        "image_urls": "[]",
    },
]

assert "قدور" in app.product_search_terms(app.normalize_text("قذور"))
assert app.correct_search_spelling(app.normalize_text("قذور")) == "قدور"
assert app.match_products_from_text("قذور هندي", products)[0]["id"] == 1
assert app.match_products_from_text("الشيء الذي يقطع الخضروات", products)[0]["id"] == 2

sent = []
unavailable = []
app.get_all_products = lambda: products
app.send_product_card = lambda recipient, product: sent.append(("card", product["id"]))
app.send_matching_products_carousel = lambda *args, **kwargs: sent.append(("carousel", [p["id"] for p in args[1]]))
app.notify_owner_unavailable_product = lambda *args, **kwargs: unavailable.append(args)
app.send_message = lambda *args, **kwargs: None
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

query = "قذور"
app.handle_customer_message("967700000000", query, app.normalize_text(query), {"type": "text"})
assert sent == [("card", 1)]
assert unavailable == []

sent.clear()
query = "الشيء الذي يقطع الخضروات"
app.handle_customer_message("967700000000", query, app.normalize_text(query), {"type": "text"})
assert sent == [("card", 2)]
assert unavailable == []
print("spelling_search_test: OK")
