import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["مشنات خضار طويلة كبيرة"]

assert product["price"] == "500"
assert product["variants"] == ""
assert "large-rectangular-vegetable-strainer-500.jpg" in product["image_urls"]
for keyword in ["مشنات خضار", "شبك خضار مستطيل", "مصفاة خضار"]:
    assert keyword in product["keywords"]

print("vegetable_strainer_product_test: OK")
