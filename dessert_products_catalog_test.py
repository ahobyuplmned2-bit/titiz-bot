import json
from pathlib import Path

import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
bowls = catalog["مطايب زجاج ومحلبية 6 حبات"]
molds = catalog["مطابع كعك أصلية كبيرة 5 حبات"]
products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]

assert bowls["price"] == "1500"
assert "مطايب محلبية" in bowls["keywords"]
assert "glass-dessert-bowls-6pcs-1500.jpg" in bowls["image_urls"]
assert molds["price"] == "500"
assert "مطابع كعك" in molds["keywords"]
assert "large-cake-molds-5pcs-500.jpg" in molds["image_urls"]

bowl_matches = app.match_products_from_text("مطايب محلبية", products)
mold_matches = app.match_products_from_text("مطابع كعك", products)
assert [item["name"] for item in bowl_matches] == [bowls["name"]]
assert [item["name"] for item in mold_matches] == [molds["name"]]

print("dessert_products_catalog_test: OK")
