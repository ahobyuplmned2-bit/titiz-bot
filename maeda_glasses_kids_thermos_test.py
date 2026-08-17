import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

expected = {
    "اقلاص عصير المائدة 6 حبات": {
        "price": "1800",
        "image_fragment": "maeda-juice-glasses-6pcs-1800.jpg",
        "keywords": ["اقلاص عصير", "المائدة", "عبوة 6"],
    },
    "ثلاجة أطفال أصلية حفظ حرارة 4 ساعات": {
        "price": "1300",
        "image_fragment": "original-kids-thermos-4hours-1300.jpg",
        "keywords": ["ثلاجة أطفال", "ترمس أطفال", "4 ساعات"],
    },
}

for name, checks in expected.items():
    product = catalog[name]
    assert product["price"] == checks["price"]
    assert checks["image_fragment"] in product["image_urls"]
    for keyword in checks["keywords"]:
        assert keyword in product["keywords"]

print("maeda_glasses_kids_thermos_test: OK")
