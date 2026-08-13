import app


assert app.is_order_detail_inquiry(app.normalize_text("ايش داخل طلبي"))
assert app.is_payment_status_inquiry(app.normalize_text("هل وصل التحويل"))
assert app.is_cancel_order_request(app.normalize_text("الغي طلبي"))
assert app.is_address_update_request(app.normalize_text("غيروا العنوان"))
assert app.is_order_edit_request(app.normalize_text("أعدل طلبي"))
assert app.is_customer_complaint(app.normalize_text("الطلب ناقص"))
assert app.extract_order_number("تفاصيل ORD-000123") == "ORD-000123"
assert app.extract_order_number("حالة الطلب 123") == "ORD-000123"
assert app.extract_order_number("تتبع 123") == "ORD-000123"
assert app.is_cancel_order_request(app.normalize_text("الغوا الطلب 123"))

order = {
    "order_number": "ORD-000123",
    "phone_number": "967700000000",
    "order_status": "جديد",
    "payment_method": "الدفع عند الاستلام",
}
sent_buttons = []
sent_messages = []
app.get_customer_orders = lambda phone_number, limit=1: [order]
app.get_order = lambda order_number: order if order_number == "ORD-000123" else None
app.send_buttons = lambda recipient, text, buttons: sent_buttons.append((recipient, text, buttons))
app.send_message = lambda recipient, text: sent_messages.append((recipient, text))
app.notify_owner_customer_request = lambda *args: None
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message(
    "967700000000",
    "الغي طلبي",
    app.normalize_text("الغي طلبي"),
    {"type": "text"},
)
assert app.user_states["967700000000"] == "awaiting_order_cancellation"
assert sent_buttons

app.update_order_status = lambda order_number, status: True
app.handle_customer_message(
    "967700000000",
    "نعم",
    app.normalize_text("نعم"),
    {"type": "interactive"},
)
assert any("تم إلغاء الطلب" in text for _, text in sent_messages)
print("order_paths_test: OK")
