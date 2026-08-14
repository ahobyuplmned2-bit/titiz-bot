import app


sent = []
cart_added = []
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None
app.send_product_card = lambda recipient, product: sent.append((recipient, product.get("name")))
app.send_matching_products_carousel = lambda recipient, products, query_key="": sent.append(
    (recipient, [product.get("name") for product in products])
)
app.notify_owner_unavailable_product = lambda *args, **kwargs: (_ for _ in ()).throw(
    AssertionError("لم يكن يجب إعلان عدم توفر المنتج")
)
app.send_message = lambda *args, **kwargs: None
app.send_cart_view = lambda recipient: sent.append((recipient, "cart"))
app.add_to_cart = lambda recipient, product_id: cart_added.append((recipient, product_id)) or True
app.interpret_customer_message = lambda sender, text: {
    "intent": "product_search",
    "confidence": 0.97,
    "search_query": "قدور هندي",
    "reply": "",
}
app.get_all_products = lambda: [
    {
        "id": 1,
        "name": "طقم قدور هندي",
        "keywords": "قدور, قذور, هندي",
        "description": "طقم قدور هندي ثقيل",
        "price": 10500,
    }
]

app.handle_customer_message(
    "967700000000",
    "قذور هندي",
    app.normalize_text("قذور هندي"),
    {"type": "text"},
)

assert sent == [("967700000000", "طقم قدور هندي")]
assert cart_added == []
print("semantic_routing_test: OK")
