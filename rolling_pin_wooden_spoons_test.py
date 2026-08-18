import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

expected = {
    "بيلان خبز": ("800", "bread-rolling-pin-800.jpg", ["بيلم خبز", "نشابة"]),
    "ملاعق خشب أبو 4": ("600", "wooden-cooking-spoons-4pieces-600.jpg", ["ملاعق خشب", "أبو 4"]),
}

for name, (price, image_fragment, keywords) in expected.items():
    product = catalog[name]
    assert product["price"] == price
    assert image_fragment in product["image_urls"]
    for keyword in keywords:
        assert keyword in product["keywords"]

print("rolling_pin_wooden_spoons_test: OK")
