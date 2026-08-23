"""تشغيل دورة تذكيرات Titiz من Render Cron خارج عملية الويب."""

import os
import sys

import requests


base_url = os.environ.get("TITIZ_WEB_URL", "").strip().rstrip("/")
cron_token = os.environ.get("FOLLOWUP_CRON_TOKEN", "").strip()
if not base_url or not cron_token:
    print("[التذكير] TITIZ_WEB_URL و FOLLOWUP_CRON_TOKEN مطلوبان")
    raise SystemExit(2)

endpoint = f"{base_url}/internal/run-followups"
try:
    response = requests.post(
        endpoint,
        headers={"X-Titiz-Followup-Token": cron_token},
        timeout=110,
    )
    print(f"[التذكير] cron status={response.status_code} body={response.text[:500]}")
    response.raise_for_status()
except requests.RequestException as exc:
    print(f"[التذكير] تعذر تشغيل endpoint: {exc}")
    raise SystemExit(1)
