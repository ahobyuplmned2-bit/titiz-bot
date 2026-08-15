import time

import app


sender = "967700000000"
message_id = f"wamid.carousel-button-{time.time_ns()}"
handled = []

app.APP_SECRET = ""
app.whatsapp.mark_as_read = lambda *args, **kwargs: True
app.whatsapp.send_typing_indicator = lambda *args, **kwargs: True
app.notify_owner = lambda *args, **kwargs: None
app.deliver_pending_replies = lambda *args, **kwargs: None
app.persist_customer_session = lambda *args, **kwargs: None
app.handle_customer_message = lambda recipient, body, normalized, message: handled.append(
    (recipient, body, normalized, message.get("type"))
)
app.time.sleep = lambda seconds: None

payload = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "id": message_id,
                    "from": sender,
                    "type": "button",
                    "button": {"payload": "variants_920", "text": "📏 اختيار الحجم"},
                }],
            },
        }],
    }],
}

response = app.app.test_client().post("/webhook", json=payload)
assert response.status_code == 200
assert handled == [(sender, "variants_920", "variants920", "button")]

print("carousel_button_webhook_test: OK")
