"""حراسة ضد إزالة إشعار الإدارة من مسار رسالة العميل النصية دون اختبار واضح."""

from pathlib import Path


source = Path("app.py").read_text(encoding="utf-8")
required_flow = '''if msg_body and original_message_type != "interactive":
            notify_owner(sender, msg_body, message_event_id=message_event_id)'''

assert required_flow in source, "تمت إزالة إشعار الإدارة من مسار رسائل العملاء النصية"
assert "enqueue_owner_notification(" in source, "إشعار الإدارة لم يعد محفوظاً قبل الإرسال"
assert "process_pending_owner_notifications_once(" in source, "إعادة محاولة إشعار الإدارة غير مفعلة"

print("test_admin_notification_guard: OK")
