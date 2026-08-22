import json
from pathlib import Path

import app

catalog = [
    {
        "id": 1,
        "name": "اقلاص استيل غير طويل",
        "keywords": "اقلاص استيل كاسات استيل اكواب",
        "description": "اقلاص للاستخدام اليومي",
    },
    {
        "id": 2,
        "name": "اقلاص استيل طويل",
        "keywords": "اقلاص كاسات اكواب استيل",
        "description": "اقلاص طويل للماء والعصير",
    },
    {
        "id": 3,
        "name": "جاك استيل",
        "keywords": "جاك استيل مطبخ",
        "description": "جاك للاستعمال اليومي",
    },
    {
        "id": 4,
        "name": "قدور استيل",
        "keywords": "قدور استيل مطبخ",
        "description": "قدور أصلية للاستخدام اليومي",
    },
]

related = app.products_related_to_image(catalog[0], catalog)
related_names = {product["name"] for product in related}

assert "اقلاص استيل غير طويل" in related_names
assert "اقلاص استيل طويل" in related_names
assert "جاك استيل" not in related_names
assert "قدور استيل" not in related_names

real_catalog = list(json.loads(Path("products.json").read_text(encoding="utf-8")).values())
juice_matches = app.match_products_from_text("اقلاص عصير المائدة 6 حبات", real_catalog)
juice_names = {product["name"] for product in juice_matches}
assert "اقلاص عصير المائدة 6 حبات" in juice_names
assert "قدور استيل" not in juice_names
assert "جاك استيل" not in juice_names

saifi_matches = app.match_products_from_text("اقلاص شاي صيفي ستار", real_catalog)
saifi_names = {product["name"] for product in saifi_matches}
expected_saifi_names = {
    "قلص شاي صيفي ستار الاصلي 6 قطع",
    "قلص شاي صيفي ستار موديل SS-49 6 قطع",
    "قلص شاي صيفي ستار موديل SS-47 6 قطع",
    "قلص شاي صيفي ستار تشكيلة العلبة 6 قطع",
}
assert saifi_names == expected_saifi_names

print("image_related_products_test: OK")
