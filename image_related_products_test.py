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

print("image_related_products_test: OK")

