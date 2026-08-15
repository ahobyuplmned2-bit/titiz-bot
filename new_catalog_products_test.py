import json
from pathlib import Path
import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
flask = catalog["ثلاجة أبو قلص الدار الأصلية - ألوان متعددة"]
chopper = catalog["فرامة خضروات مروحية من المائدة"]

assert flask["price"] == "1600"
assert "أبو قلص" in flask["keywords"]
assert "التاج" not in flask["keywords"]
assert "al-dar-tea-flask-cups-1600.jpg" in flask["image_urls"]

assert chopper["price"] == "3000"
assert "فرامة مروحية" in chopper["keywords"]
assert "سرعتين" in chopper["keywords"]
assert "almaeda-fan-chopper-3000.jpg" in chopper["image_urls"]

products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]
flask_matches = app.match_products_from_text("ابو قلص", products)
chopper_matches = app.match_products_from_text("فرامة مروحية", products)
assert [item["name"] for item in flask_matches] == [flask["name"]]
assert [item["name"] for item in chopper_matches] == [chopper["name"]]

print("new_catalog_products_test: OK")
