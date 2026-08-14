import app


sent = []
app.send_product_request_menu = lambda recipient: sent.append(("catalog", recipient))
app.send_payment_choice = lambda recipient: sent.append(("payment", recipient))
app.send_price_inquiry_response = lambda recipient: sent.append(("discount", recipient))
app.request_customer_complaint = lambda recipient: sent.append(("complaint", recipient))
app.send_guided_help = lambda recipient, intro="": sent.append(("guided", recipient, intro))
app.send_response = lambda recipient, response: sent.append(("service", recipient, response["reply"]))
app.find_response = lambda keyword: {"reply": f"خدمة: {keyword}"}

phone = "967700000555"
for intent, expected in [
    ("catalog", "catalog"),
    ("payment", "payment"),
    ("discount", "discount"),
    ("complaint", "complaint"),
    ("shipping", "service"),
    ("location", "service"),
    ("warranty", "service"),
    ("out_of_scope", "guided"),
]:
    sent.clear()
    handled = app.route_semantic_intent(
        phone,
        "رسالة اختبار",
        {"intent": intent, "confidence": 0.9, "search_query": "", "reply": "رد مختصر"},
        [],
    )
    assert handled is True
    assert sent[0][0] == expected, (intent, sent)

print("service_intent_test: OK")
