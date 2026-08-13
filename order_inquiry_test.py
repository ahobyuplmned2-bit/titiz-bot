import app


phrases = [
    "ايش طلبت منك",
    "وين طلبي",
    "ايش رفعت لسه",
    "الطلبات حقي",
    "حالة طلبي",
    "متابعة الشحنه",
]

for phrase in phrases:
    assert app.is_order_inquiry(app.normalize_text(phrase)), phrase

assert not app.is_order_inquiry(app.normalize_text("ثلاجة شاي"))
assert not app.is_order_inquiry(app.normalize_text("قلص"))

sent_for_orders = []
app.send_customer_orders = lambda recipient: sent_for_orders.append(recipient)
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

for phrase in ["ايش طلبت منك", "وين طلبي", "ايش رفعت لسه"]:
    app.handle_customer_message(
        "967700000000",
        phrase,
        app.normalize_text(phrase),
        {"type": "text"},
    )

assert sent_for_orders == ["967700000000"] * 3
print("order_inquiry_test: OK")
