import time

import app


message_id = f"wamid.interactive-rate-{time.time_ns()}"
handled = []
owner_notifications = []

app.APP_SECRET = ""
app.whatsapp.mark_as_read = lambda *args, **kwargs: True
app.whatsapp.send_typing_indicator = lambda *args, **kwargs: True
app.notify_owner = lambda *args, **kwargs: owner_notifications.append(args)
app.handle_customer_message = lambda sender, body, normalized, message: handled.append(
    (sender, body, normalized, message.get("type"))
)
app.persist_customer_session = lambda *args, **kwargs: None
app.deliver_pending_replies = lambda *args, **kwargs: None
app.time.sleep = lambda seconds: None

payload = {
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "id": message_id,
                    "from": "967700000000",
                    "type": "interactive",
                    "interactive": {
                        "type": "button_reply",
                        "button_reply": {"id": "variants_909", "title": "📏 اختيار الحجم"},
                    },
                }],
            },
        }],
    }],
}

client = app.app.test_client()
assert client.post("/webhook", json=payload).status_code == 200
assert client.post("/webhook", json=payload).status_code == 200
assert handled == [("967700000000", "variants_909", "variants909", "interactive")]
assert owner_notifications == []

print("interactive_webhook_dedup_test: OK")
