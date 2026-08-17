import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

expected = {
    "غطاء كوع رائحة حمام تركي أصلي أبو فتحتين": ("500", "turkish-double-opening-toilet-drain-cover-500.jpg", ["غطاء رائحة حمام", "أبو فتحتين"]),
    "مساحات زجاج تركية أصلية": ("500", "turkish-glass-squeegee-small-large.jpg", ["سحاب زجاج", "صغير", "كبير"]),
    "خلاط كهربائي أصلي المائدة M80": ("5000", "original-maeda-hand-mixer-sk6621-5000.jpg", ["خلاط يدوي", "SK-6621"]),
    "جزوات دلة استيل أصلية 3 أحجام": ("1500", "original-stainless-steel-dallahs-3sizes.jpg", ["جزوات دلة", "كبير"]),
    "اقلاص عصير مربع 6 حبات": ("1500", "square-juice-glasses-6pcs-1500.jpg", ["اقلاص عصير مربع", "عبوة 6"]),
    "طباخة المائدة M60X نحاس 3 عيون": ("22500", "original-maeda-stove-m60x-copper-3burners-22500.jpg", ["طباخة نحاس", "M60X"]),
}

for name, (price, image_fragment, keywords) in expected.items():
    product = catalog[name]
    assert product["price"] == price
    assert image_fragment in product["image_urls"]
    for keyword in keywords:
        assert keyword in product["keywords"]

assert {variant["price"] for variant in catalog["مساحات زجاج تركية أصلية"]["variants"]} == {"500", "700"}
assert {variant["price"] for variant in catalog["جزوات دلة استيل أصلية 3 أحجام"]["variants"]} == {"1500", "1800", "2000"}

print("pending_home_products_test: OK")
