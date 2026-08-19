"""اختبار صيغة إشعار الإدارة من دون إرسال رسالة واتساب حقيقية."""

import os

os.environ["DISABLE_PRODUCT_FOLLOWUP_WORKER"] = "1"

import app


captured = []
app.get_customer = lambda phone: {"name": "أحمد"} if phone == "9677712282204" else None
app.send_message = lambda target, text: captured.append((target, text)) or True

app.notify_owner("9677712282204", "أريد أدوات منزلية", message_event_id=2)

assert len(captured) == 1
target, notification = captured[0]
assert target == app.OWNER_NUMBER
assert "📨 *رسالة جديدة*" in notification
assert "👤 العميل: أحمد" in notification
assert "📞 الرقم: 9677712282204" in notification
assert "💬 الرسالة:\nأريد أدوات منزلية" in notification
assert "🕒 التاريخ والوقت:" in notification
assert "🆔 رقم الرسالة: 0002" in notification
assert notification.endswith("━━━━━━━━━━━━")

print("اختبار إشعار الإدارة المنظم: ناجح")
