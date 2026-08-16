import json
from pathlib import Path


catalog_path = Path(__file__).with_name("products.json")
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
product = catalog["مشنات عصاير أصلية بطن واحد"]

assert product["price"] == "500"
assert product["variants"] == ""
assert "juice-strainer-original-500.jpg" in product["image_urls"]
for keyword in ["مشنات عصاير", "مصفاة عصير", "مصفاة شاي", "بطن واحد"]:
    assert keyword in product["keywords"]

print("juice_strainer_product_test: OK")
