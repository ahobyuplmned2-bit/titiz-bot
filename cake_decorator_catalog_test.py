import json
from pathlib import Path

import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
kit = catalog["طقم مزاز كريمة مع فرشاة بيض"]
products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]

assert kit["price"] == "500"
assert "مزاز كريمة" in kit["keywords"]
assert "فرشاة بيض" in kit["keywords"]
assert "cake-decorator-kit-500.jpg" in kit["image_urls"]

matches = app.match_products_from_text("مزاز كريمة", products)
assert [item["name"] for item in matches] == [kit["name"]]

print("cake_decorator_catalog_test: OK")
