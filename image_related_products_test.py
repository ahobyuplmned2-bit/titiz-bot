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
    "قلص شاي صيفي ستار موديل SS-05 6 قطع",
}
assert saifi_names == expected_saifi_names

tea_glass_matches = app.match_products_from_text("قلاصات حق الشاي", real_catalog)
tea_glass_names = {product["name"] for product in tea_glass_matches}
assert expected_saifi_names <= tea_glass_names
assert "كتلي شاي ستيل أبو صفارة" not in tea_glass_names
assert "قدور استيل" not in tea_glass_names

tea_kettle_matches = app.match_products_from_text("كتالي من حق الشاي", real_catalog)
tea_kettle_names = {product["name"] for product in tea_kettle_matches}
assert "كتلي شاي ستيل أبو صفارة" in tea_kettle_names
assert not expected_saifi_names & tea_kettle_names
assert "قدور استيل" not in tea_kettle_names

broom_matches = app.match_products_from_text("مكنسة تركي ريش رطب", real_catalog)
broom_names = {product["name"] for product in broom_matches}
assert "مكانس تركي ريش رطب" in broom_names
assert "موب بلاط مع العصا" not in broom_names

handled_scourer_matches = app.match_products_from_text("سلك غسيل ابو مقبض", real_catalog)
handled_scourer_names = {product["name"] for product in handled_scourer_matches}
assert "سلك غسيل أبو مقبض الأصلي" in handled_scourer_names
assert "موب بلاط مع العصا" not in handled_scourer_names

onion_matches = app.match_products_from_text("عصارات بصل", real_catalog)
onion_names = {product["name"] for product in onion_matches}
assert "عصارة البصل الفريدة الأصلية" in onion_names
assert "قدور استيل" not in onion_names
assert "جاك استيل" not in onion_names

fava_matches = app.match_products_from_text("ممهد فول استيل", real_catalog)
fava_names = {product["name"] for product in fava_matches}
assert "ممهَد فول استيل أصلي" in fava_names
assert "قدور استيل" not in fava_names
assert "اقلاص استيل غير طويل" not in fava_names

print("image_related_products_test: OK")
