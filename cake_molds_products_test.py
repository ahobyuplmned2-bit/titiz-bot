import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

expected = {
    "مطابع كعك ومعمول": ("800", "maamoul-mold-6pieces-800.jpg", ["مطابع معمول", "أبو 8"]),
    "مطابع كعك إيلابيو أبو 4": ("500", "ilafio-cake-molds-4pieces-500.jpg", ["إيلابيو", "أبو 4"]),
    "مطابع كعك صغيرة أبو 10": ("500", "small-cake-molds-10pieces-500.jpg", ["مطابع كعك صغيرة", "أبو 10"]),
}

for name, (price, image_fragment, keywords) in expected.items():
    product = catalog[name]
    assert product["price"] == price
    assert image_fragment in product["image_urls"]
    for keyword in keywords:
        assert keyword in product["keywords"]

assert {variant["price"] for variant in catalog["مطابع كعك ومعمول"]["variants"]} == {"800", "1000"}

print("cake_molds_products_test: OK")
