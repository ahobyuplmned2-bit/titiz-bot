"""اختبار أن فشل إشعار الإدارة لا يفقد رسالة العميل وأن الدورة التالية تعيد الإرسال."""

import os
import sqlite3

os.environ["DISABLE_PRODUCT_FOLLOWUP_WORKER"] = "1"

import app
from database import DB_PATH, db_lock, init_db


init_db()
event_id = 990001
with db_lock:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM owner_notification_outbox WHERE message_event_id = ?", (event_id,))
    conn.commit()
    conn.close()

attempts = []
responses = [False, "wamid.owner-notification-retry"]
app.get_customer = lambda _: {"name": "عميل اختبار"}
app.reserve_owner_notification_sequence = lambda *_: 9001
app.OWNER_NOTIFICATION_RETRY_BASE_SECONDS = 0
app.OWNER_NOTIFICATION_RETRY_MAX_SECONDS = 0
app.send_message = lambda target, text: attempts.append((target, text)) or responses.pop(0)

assert not app.notify_owner("967700000001", "رسالة اختبار", message_event_id=event_id)
assert len(attempts) == 1
assert app.process_pending_owner_notifications_once() == 1
assert len(attempts) == 2

with db_lock:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT state, attempt_count, sent_at, last_error FROM owner_notification_outbox WHERE message_event_id = ?",
        (event_id,),
    ).fetchone()
    conn.close()

assert row and row[0] == "sent"
assert row[1] == 1
assert row[2] is not None
assert row[3] is None
print("test_owner_notification_retry: OK")
