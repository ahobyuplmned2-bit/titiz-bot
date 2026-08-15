import hashlib
import hmac
import json

import app


sent = []
app.APP_SECRET = "test-app-secret"
app.processed_messages.clear()
app.claim_processed_webhook_message = lambda message_id, timestamp: True
app.record_contact = lambda sender: None
app.record_message_event = lambda **kwargs: 1
app.persist_customer_session = lambda sender: None
app.whatsapp.mark_as_read = lambda message_id: True
app.whatsapp.send_typing_indicator = lambda message_id: True
app.send_message = lambda recipient, text: sent.append((recipient, text)) or True
app.notify_owner = lambda sender, text: None
app.deliver_pending_replies = lambda sender: None
app.time.sleep = lambda seconds: None

payload = {
    "entry": [{"changes": [{"value": {"messages": [{
        "id": "test-unsupported-message",
        "from": "967700000009",
        "type": "sticker",
    }]}}]}]
}
raw = json.dumps(payload).encode("utf-8")
client = app.app.test_client()

invalid = client.post("/webhook", data=raw, content_type="application/json")
assert invalid.status_code == 403
assert sent == []

signature = "sha256=" + hmac.new(app.APP_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
valid = client.post(
    "/webhook",
    data=raw,
    content_type="application/json",
    headers={"X-Hub-Signature-256": signature},
)
assert valid.status_code == 200
assert sent == []

handled = []
app.handle_customer_message = lambda sender, body, normalized, message: handled.append(
    (sender, body, normalized, message.get("type"))
)
text_payload = {
    "entry": [{"changes": [{"value": {"messages": [{
        "id": "test-text-message",
        "from": "967700000010",
        "type": "text",
        "text": {"body": "قذور هندي"},
    }]}}]}]
}
text_raw = json.dumps(text_payload).encode("utf-8")
text_signature = "sha256=" + hmac.new(app.APP_SECRET.encode("utf-8"), text_raw, hashlib.sha256).hexdigest()
text_response = client.post(
    "/webhook",
    data=text_raw,
    content_type="application/json",
    headers={"X-Hub-Signature-256": text_signature},
)
assert text_response.status_code == 200
assert handled == [("967700000010", "قذور هندي", app.normalize_text("قذور هندي"), "text")]

print("webhook_security_test: OK")
