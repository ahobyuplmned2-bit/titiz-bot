import json
from pathlib import Path

import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
peeler = catalog["مقشرة بطاط متعددة الاستخدام"]
flask = catalog["ثلاجة استيل أصلية أبو هسه من المائدة"]
products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]

assert peeler["price"] == "300"
assert "متعددة الاستخدام" in peeler["keywords"]
assert "multiuse-potato-peeler-300.jpg" in peeler["image_urls"]
assert flask["price"] == "4500"
assert "ابو هسة" in flask["keywords"]
assert "almaeda-abu-hassa-flask-4500.jpg" in flask["image_urls"]

peeler_matches = app.match_products_from_text("مقشرة متعددة الاستخدام", products)
flask_matches = app.match_products_from_text("ثلاجة ابو هسه", products)
assert [item["name"] for item in peeler_matches] == [peeler["name"]]
assert [item["name"] for item in flask_matches] == [flask["name"]]

print("peeler_flask_catalog_test: OK")
