"""اختبار تنبيه الإدارة للمحادثة غير المتابعة دون إرسال واتساب فعلي."""

import os
import tempfile

os.environ["DISABLE_PRODUCT_FOLLOWUP_WORKER"] = "1"

import app
import database


with tempfile.TemporaryDirectory() as temp_dir:
    database.DB_PATH = os.path.join(temp_dir, "followup-alert-test.db")
    database.init_db()
    database.schedule_customer_followup(
        "9677712282204",
        "خلاط كهربائي",
        delay_seconds=60,
        context_text="أريد خلاط كهربائي",
        last_message_at=1_786_000_000,
    )
    followup = database.get_customer_followup("9677712282204")
    assert followup["last_message_at"] == 1_786_000_000

followup = {
    "phone_number": "9677712282204",
    "product_name": "خلاط كهربائي",
    "context_text": "أريد خلاط كهربائي",
    "last_message_at": 1_786_000_000,
    "due_at": 1,
    "followup_kind": "satisfaction",
}
events = []
app.get_due_customer_followups = lambda: [followup]
app.claim_customer_followup = lambda phone, due: phone == "9677712282204" and due == 1
app.mark_customer_followup_sent = lambda phone, due: phone == "9677712282204" and due == 1
app.notify_owner_unfollowed_conversation = lambda item: events.append(("admin", item["phone_number"])) or True
app.send_product_followup = lambda phone, product, context: events.append(("customer", phone, product, context)) or True

app.process_due_customer_followups_once()

assert events == [
    ("admin", "9677712282204"),
    ("customer", "9677712282204", "خلاط كهربائي", "أريد خلاط كهربائي"),
]
print("اختبار تنبيه الإدارة للمحادثة غير المتابعة: ناجح")
