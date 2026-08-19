"""اختبار معزول لحفظ ذاكرة العميل وتذكير واحد دون إرسال واتساب."""

import importlib
import os
import sqlite3
import sys
import tempfile
import time


with tempfile.TemporaryDirectory() as temporary_directory:
    database_path = os.path.join(temporary_directory, "titiz-memory-test.db")
    os.environ["DATABASE_PATH"] = database_path
    sys.modules.pop("database", None)
    database = importlib.import_module("database")

    assert database.DB_PATH == database_path
    database.init_db()

    database.save_user_session(
        "967700000000",
        "product_context",
        {"last_product_name": "طقم ملاعق", "last_topic": "سؤال السعر"},
    )
    session = database.load_user_session("967700000000")
    assert session["state"] == "product_context"
    assert session["data"]["last_product_name"] == "طقم ملاعق"

    database.schedule_customer_followup(
        "967700000000",
        "طقم ملاعق",
        delay_seconds=60,
        context_text="هل يوجد مقاس أكبر؟",
    )
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(customer_followups)").fetchall()
        }
        assert "context_text" in columns
        connection.execute(
            "UPDATE customer_followups SET due_at = ? WHERE phone_number = ?",
            (time.time() - 1, "967700000000"),
        )
        connection.commit()

    due_followups = database.get_due_customer_followups()
    assert len(due_followups) == 1
    followup = due_followups[0]
    assert followup["product_name"] == "طقم ملاعق"
    assert followup["context_text"] == "هل يوجد مقاس أكبر؟"
    assert database.mark_customer_followup_sent("967700000000", followup["due_at"])
    assert not database.mark_customer_followup_sent("967700000000", followup["due_at"])

    database.schedule_customer_followup("967700000002", "خلاط كهربائي", delay_seconds=60)
    database.cancel_customer_followup("967700000002")
    assert database.get_customer_followup("967700000002") is None

    # محاكاة إعادة تشغيل العملية مع الإبقاء على مسار القاعدة نفسه.
    sys.modules.pop("database", None)
    restarted_database = importlib.import_module("database")
    restored_session = restarted_database.load_user_session("967700000000")
    assert restored_session["data"]["last_topic"] == "سؤال السعر"

print("PASS: memory persistence and one-shot followup")


# لا نستخدم اتصال واتساب في هذا الاختبار؛ نتحقق فقط من الرسالة التي سيحاول البوت إرسالها.
with tempfile.TemporaryDirectory() as temporary_directory:
    os.environ["DATABASE_PATH"] = os.path.join(temporary_directory, "titiz-app-test.db")
    os.environ["FOLLOWUP_WORKER_ENABLED"] = "false"
    sys.modules.pop("database", None)
    sys.modules.pop("app", None)
    app = importlib.import_module("app")

    captured = {}

    def capture_buttons(phone_number, text, buttons):
        captured["phone_number"] = phone_number
        captured["text"] = text
        captured["buttons"] = buttons
        return True

    app.send_buttons = capture_buttons
    app.user_sessions["967700000001"] = {}
    app.schedule_product_followup("967700000001", "طقم ملاعق")
    assert app.user_sessions["967700000001"]["last_conversation_topic"] == "طقم ملاعق"
    app.send_product_followup("967700000001", "طقم ملاعق")
    assert "طقم ملاعق" in captured["text"]
    assert captured["buttons"][0]["id"] == app.PRODUCT_FOLLOWUP_CONTINUE_ID
    assert captured["buttons"][1]["id"] == app.PRODUCT_FOLLOWUP_STOP_ID

    app.send_product_followup("967700000001", "", "هل يوجد توصيل إلى إب؟")
    assert "هل يوجد توصيل إلى إب؟" in captured["text"]

print("PASS: followup message content and session topic")
