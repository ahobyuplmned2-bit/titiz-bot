import hashlib
import hmac
import json

import app


app.APP_SECRET = "document-image-test-secret"
app.processed_messages.clear()
app.user_states.clear()
app.user_sessions.clear()
app.claim_processed_webhook_message = lambda message_id, timestamp: True
app.record_contact = lambda sender: None
app.record_message_event = lambda **kwargs: 1
app.persist_customer_session = lambda sender: None
app.whatsapp.mark_as_read = lambda message_id: True
app.whatsapp.send_typing_indicator = lambda message_id: True
app.deliver_pending_replies = lambda sender: None
app.notify_owner = lambda sender, text: None
app.time.sleep = lambda seconds: None

sent_messages = []
sent_cards = []
app.send_message = lambda sender, text: sent_messages.append((sender, text)) or True
app.send_product_card = lambda sender, product: sent_cards.append((sender, product)) or True
app.analyze_product_image = lambda sender, message, caption="": {
    "kind": "product",
    "product": {"id": 501, "name": "منتج تجريبي", "price": "500", "image_urls": "[]"},
}
app.products_related_to_image = lambda product, products: [product]

queued_tasks = []

class CapturedThread:
    def __init__(self, target, args=(), daemon=False, name=None):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.name = name

    def start(self):
        queued_tasks.append(self)

app.Thread = CapturedThread

payload = {
    "entry": [{"changes": [{"value": {"messages": [{
        "id": "document-image-message",
        "from": "967700000222",
        "type": "document",
        "document": {"id": "document-image-id", "mime_type": "image/jpeg", "filename": "product.jpg"},
    }]}}]}]
}
raw = json.dumps(payload).encode("utf-8")
signature = "sha256=" + hmac.new(app.APP_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
response = app.app.test_client().post(
    "/webhook",
    data=raw,
    content_type="application/json",
    headers={"X-Hub-Signature-256": signature},
)

assert response.status_code == 200
assert queued_tasks, "يجب أن يعيد webhook الاستجابة قبل معالجة صورة العميل الطويلة"
assert not sent_cards, "لا ينبغي معالجة الصورة داخل طلب webhook نفسه"
queued_tasks[0].target(*queued_tasks[0].args)
assert sent_cards and sent_cards[0][1]["id"] == 501
assert not any("النصوص والصور والرسائل الصوتية" in text for _, text in sent_messages)
print("document_product_image_test: OK (webhook returns immediately and image is processed in background)")
