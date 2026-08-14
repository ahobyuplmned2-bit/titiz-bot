import app


queries = [
    "عصارات",
    "عصاره",
    "العصارات",
    "هل متوفر لديكم عصارات",
    "هل عندكم عصارة",
    "وين العصارات",
    "عصارات بلاستيك",
    "عصارات استيل",
    "عصارة خضار",
    "عصارات يدوية",
]

for query in queries:
    terms = app.product_search_terms(app.normalize_text(query))
    assert "عصارات" in terms or "عصاره" in terms, query

fake_product = {
    "id": "juicer-1",
    "name": "عصارة الدار بلاستيك مدورة أصلية",
    "keywords": "عصارة,عصارات,عصارات بلاستيك,عصارة مدورة",
    "price": "1000",
    "image_urls": "[]",
}
carousel_calls = []
unavailable = []
app.get_all_products = lambda: [fake_product]
app.send_product_card = lambda recipient, product: carousel_calls.append(("card", product))
app.send_matching_products_carousel = lambda recipient, products, query_key="": carousel_calls.append(
    ("carousel", products, query_key)
)
app.notify_owner_unavailable_product = lambda *args, **kwargs: unavailable.append(args)
app.send_message = lambda *args, **kwargs: None
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

query = "هل متوفر لديكم عصارات"
app.handle_customer_message(
    "967700000000",
    query,
    app.normalize_text(query),
    {"type": "text"},
)

assert carousel_calls or any(call[0] == "card" for call in carousel_calls)
assert unavailable == []
print("juicer_search_test: OK")
