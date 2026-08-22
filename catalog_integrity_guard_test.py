import catalog_integrity_guard as guard


valid_catalog = {
    name: {
        "price": "1400",
        "image_urls": f'["https://example.test/assets/{image_name}"]',
    }
    for name, image_name in guard.PROTECTED_GROUPS["تشكيلات اقلاص شاي صيفي ستار"]["products"].items()
}

# نضيف سجلات كافية لاختبار الحد المرجعي دون استعمال بيانات حقيقية.
for index in range(guard.MINIMUM_PRODUCT_COUNT - len(valid_catalog)):
    valid_catalog[f"منتج اختبار {index}"] = {"price": "1", "image_urls": '["https://example.test/a.jpg"]'}

assert not guard.validate_catalog(valid_catalog)

missing_model = dict(valid_catalog)
missing_model.pop("قلص شاي صيفي ستار موديل SS-49 6 قطع")
assert guard.validate_catalog(missing_model)

wrong_price = {key: dict(value) for key, value in valid_catalog.items()}
wrong_price["قلص شاي صيفي ستار موديل SS-47 6 قطع"]["price"] = "1200"
assert guard.validate_catalog(wrong_price)

print("catalog_integrity_guard_test: OK")
