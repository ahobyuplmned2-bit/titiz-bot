import app


SENDER = "967700000123"
PRODUCT = next(
    dict(product)
    for product in app.get_all_products()
    if app.parse_product_price(product.get("price")) is not None and not app.product_variants(product)
)

sent_messages = []
sent_buttons = []
added_products = []

app.user_states.clear()
app.user_sessions.clear()
app.send_message = lambda to, text: sent_messages.append((to, text)) or True
app.send_buttons = lambda to, text, buttons: sent_buttons.append((to, text, buttons)) or True
app.send_variant_list = lambda to, product: sent_messages.append((to, "VARIANTS")) or True
app.add_to_cart = lambda to, product_id, quantity=1, *args: added_products.append((to, product_id, quantity)) or True
app.cancel_customer_followup = lambda *args, **kwargs: None

# يغطي نفس النص الظاهر في المحادثة: «اضافه» بلا همزة أو تاء مربوطة.
app.user_states[SENDER] = "product_context"
app.user_sessions[SENDER] = {"last_product": PRODUCT}
app.handle_customer_message(SENDER, "اضافه", app.normalize_text("اضافه"), {"type": "text"})

assert added_products == [(SENDER, PRODUCT["id"], 1)]
assert any("تم إضافة" in text for _, text in sent_messages)
assert not any("المنتجات المطابقة" in text for _, text in sent_messages)

# نتائج البحث المتعددة تطلب اختيار المنتج أولاً ولا تفترض البطاقة الأولى.
app.user_states.clear()
app.user_sessions.clear()
app.send_list = lambda *args, **kwargs: True
app.send_matching_products_carousel(SENDER, [PRODUCT, {**PRODUCT, "id": 98766, "name": "طقم قدور آخر"}], "قدور")
assert app.user_states[SENDER] == "search_results"
assert app.user_sessions[SENDER]["matching_product_ids"] == [PRODUCT["id"], 98766]

print("text_add_context_test: OK")
