import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["مدقات معدن أبو جلاس أصلية 3 أحجام"]

assert product["price"] == "2500"
assert [(item["name"], item["price"]) for item in product["variants"]] == [
    ("صغير", "2500"),
    ("وسط", "3500"),
    ("كبير", "4000"),
]
assert "abu-jalas-metal-mortars-3sizes.jpg" in product["image_urls"]
for keyword in ["مدقات معدن", "أبو جلاس", "هاون معدن"]:
    assert keyword in product["keywords"]

print("metal_mortars_product_test: OK")
