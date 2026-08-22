import change_guard


before = {
    "منتج أ": {"name": "منتج أ", "price": "100", "image_urls": "[\"https://example.test/a.jpg\"]", "image_id": ""},
    "منتج ب": {"name": "منتج ب", "price": "200", "image_urls": "[\"https://example.test/b.jpg\"]", "image_id": ""},
}
after = {
    "منتج أ": {"name": "منتج أ", "price": "150", "image_urls": "[\"https://example.test/a.jpg\"]", "image_id": ""},
    "منتج ب": {"name": "منتج ب", "price": "200", "image_urls": "[\"https://example.test/b.jpg\"]", "image_id": ""},
}

assert change_guard.changed_products(before, after) == {"منتج أ"}
assert not change_guard.validate_product_schema(after)
assert change_guard.validate_product_schema({"خطأ": {"name": "", "price": "", "image_urls": "", "image_id": ""}})

print("change_guard_test: OK")

