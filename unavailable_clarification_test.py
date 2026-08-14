import app


sent = []
owner_notifications = []
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None
app.get_all_products = lambda: []
app.find_response = lambda normalized: None
app.interpret_customer_message = lambda recipient, text: None
app.send_message = lambda recipient, text: sent.append((recipient, text))
app.notify_owner_unavailable_product = lambda recipient, text, source="text": owner_notifications.append((recipient, text, source))

sender = "967700000111"
app.user_states.pop(sender, None)
app.user_sessions.pop(sender, None)
message = {"type": "text"}

app.handle_customer_message(sender, "شيء غريب للمطبخ", app.normalize_text("شيء غريب للمطبخ"), message)
assert "غير متوفر" not in sent[-1][1]
assert "اكتبي اسمه" in sent[-1][1]
assert owner_notifications == []

app.handle_customer_message(sender, "شيء غريب للمطبخ", app.normalize_text("شيء غريب للمطبخ"), message)
assert "غير متوفر" not in sent[-1][1]
assert "للمراجعة" in sent[-1][1]
assert len(owner_notifications) == 1
print("unavailable_clarification_test: OK")
