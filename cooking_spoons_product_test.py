import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

expected = {
    "ملاعق ياباني أصلية يد خشب للطبخ": {
        "price": "700",
        "image_fragment": "japanese-wood-handle-cooking-spoons.jpg",
        "keywords": ["ملاعق ياباني", "يد خشب", "ملعقة مشن"],
    },
    "ملاعق طبخ خشب أحمر": {
        "price": "250",
        "image_fragment": "red-wood-cooking-spoon.jpg",
        "keywords": ["ملاعق طبخ خشب", "خشب احمر", "250 ريال"],
    },
}

for name, checks in expected.items():
    product = catalog[name]
    assert product["price"] == checks["price"]
    assert checks["image_fragment"] in product["image_urls"]
    for keyword in checks["keywords"]:
        assert keyword in product["keywords"]

print("cooking_spoons_product_test: OK")
