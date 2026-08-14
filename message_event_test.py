import os

os.environ["DASHBOARD_API_TOKEN"] = "test-dashboard-token"

from app import app
from database import get_message_events, init_db, record_message_event, update_message_event


init_db()
event_id = record_message_event(
    whatsapp_message_id="test-message-1",
    direction="inbound",
    phone_number="967700000000",
    message_type="text",
    body="وين طلبي",
    normalized_body="وين طلبي",
    intent="orders",
    intent_confidence=0.86,
)
assert event_id
assert update_message_event(event_id, ai_status="skipped", response_text="تم تسجيل الرسالة")
assert get_message_events(limit=5, phone_number="967700000000")[0]["intent"] == "orders"

client = app.test_client()
assert client.get("/admin/api/messages").status_code == 401
headers = {"X-Titiz-Admin-Token": "test-dashboard-token"}
assert client.get("/admin/api/messages?limit=5", headers=headers).status_code == 200
assert client.get("/admin/api/summary", headers=headers).status_code == 200
assert client.get("/admin/api/products", headers=headers).status_code == 200
print("message_event_test: OK")
