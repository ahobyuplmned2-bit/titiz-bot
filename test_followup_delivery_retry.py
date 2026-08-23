import importlib
import os
from pathlib import Path
import sys
import tempfile
import time


with tempfile.TemporaryDirectory() as temporary_directory:
    os.environ["DATABASE_PATH"] = os.path.join(temporary_directory, "followup-retry.db")
    os.environ["FOLLOWUP_WORKER_ENABLED"] = "false"
    sys.modules.pop("database", None)
    sys.modules.pop("app", None)
    database = importlib.import_module("database")
    app = importlib.import_module("app")

    phone = "967700000099"
    database.schedule_customer_followup(
        phone,
        "منتج تجريبي",
        delay_seconds=60,
        last_message_at=time.time() - 120,
    )
    app.notify_owner_unfollowed_conversation = lambda followup: True
    app.send_product_followup = lambda *args, **kwargs: False
    app.process_due_customer_followups_once()
    first = database.get_customer_followup(phone)
    assert first["sent_at"] is None, "لا يجوز تعليم التذكير مرسلاً عند فشل واتساب"
    assert first["attempt_count"] == 1
    assert first["last_error"]

    app.send_product_followup = lambda *args, **kwargs: True
    app.process_due_customer_followups_once()
    second = database.get_customer_followup(phone)
    assert second["sent_at"] is not None, "يجب تعليم التذكير مرسلاً بعد نجاح واتساب"
    assert second["attempt_count"] == 2

    app.FOLLOWUP_CRON_TOKEN = "test-token"
    with app.app.test_client() as client:
        assert client.post("/internal/run-followups").status_code == 401
        response = client.post(
            "/internal/run-followups",
            headers={"X-Titiz-Followup-Token": "test-token"},
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is True

render_yaml = Path("render.yaml").read_text(encoding="utf-8")
assert "type: cron" in render_yaml
assert "whatsapp-bot-titiz-followups" in render_yaml
assert "schedule: \"*/5 * * * *\"" in render_yaml
assert "python run_followups_cron.py" in render_yaml

print("test_followup_delivery_retry: OK")
