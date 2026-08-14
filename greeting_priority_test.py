import app


greetings = [
    "هلو",
    "هلو والله",
    "الو",
    "هلا",
    "مرحبا",
    "السلام عليكم",
    "hello",
]

for phrase in greetings:
    response = app.find_response(app.normalize_text(phrase))
    assert response and response["reply"], phrase
    assert "غير متوفر" not in response["reply"], phrase

sent_responses = []
unavailable = []
app.send_response = lambda recipient, response: sent_responses.append((recipient, response))
app.notify_owner_unavailable_product = lambda *args, **kwargs: unavailable.append(args)
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None
app.interpret_customer_message = lambda recipient, text: None

app.handle_customer_message(
    "967700000000",
    "هلو",
    app.normalize_text("هلو"),
    {"type": "text"},
)

assert sent_responses
assert unavailable == []
assert "غير متوفر" not in sent_responses[0][1]["reply"]
print("greeting_priority_test: OK")
