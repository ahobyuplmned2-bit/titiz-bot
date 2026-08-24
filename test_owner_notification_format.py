"""اختبار صيغة إشعار الإدارة من دون إرسال رسالة واتساب حقيقية."""

import os
import re
import sqlite3

os.environ["DISABLE_PRODUCT_FOLLOWUP_WORKER"] = "1"

import app
from database import DB_PATH, db_lock, init_db


init_db()
event_ids = (920001, 920002, 920003)
with db_lock:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "DELETE FROM owner_notification_outbox WHERE message_event_id IN (?, ?, ?)",
        event_ids,
    )
    conn.commit()
    conn.close()


captured = []
app.get_customer = lambda phone: {"name": "أحمد"} if phone == "9677712282204" else None
app.send_message = lambda target, text: captured.append((target, text)) or True
sequence_numbers = iter([1, 2, 3])
app.reserve_owner_notification_sequence = lambda phone, event_id: next(sequence_numbers)

app.notify_owner("9677712282204", "أريد أدوات منزلية", message_event_id=event_ids[0])
app.notify_owner("9677712282204", "أريد قدور", message_event_id=event_ids[1])
app.notify_owner("9677712282204", "أريد خلاط", message_event_id=event_ids[2])

assert len(captured) == 3
target, notification = captured[0]
assert target == app.OWNER_NUMBER
assert "📨 *رسالة جديدة*" in notification
assert "👤 العميل: أحمد" in notification
assert "📞 الرقم: 9677712282204" in notification
assert "💬 الرسالة:\nأريد أدوات منزلية" in notification
assert "🕒 التاريخ والوقت:" in notification
assert re.search(r"🕒 التاريخ والوقت: \d{2}-\d{2}-\d{4}، \d{2}:\d{2}", notification)
assert "🆔 رقم الرسالة: 0001" in notification
assert notification.endswith("━━━━━━━━━━━━")
assert "🆔 رقم الرسالة: 0002" in captured[1][1]
assert "🆔 رقم الرسالة: 0003" in captured[2][1]

print("اختبار إشعار الإدارة المنظم: ناجح")
