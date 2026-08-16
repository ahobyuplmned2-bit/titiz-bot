import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["طشات غسيل الهلال 5 مقاسات"]

assert product["price"] == "1000"
assert [(item["name"], item["price"]) for item in product["variants"]] == [
    ("مقاس 1", "1000"),
    ("مقاس 2", "1300"),
    ("مقاس 3", "1500"),
    ("مقاس 4", "1700"),
    ("مقاس 5", "2000"),
]
assert "al-hilal-washing-bowls-5sizes.jpg" in product["image_urls"]
for keyword in ["طشات غسيل", "طشت صابون", "مقاس 5"]:
    assert keyword in product["keywords"]

print("washing_bowls_product_test: OK")
