from database import get_all_products

import app

products = get_all_products()
for query, expected in (("مشنات", "مشنات استيل عصاير"), ("اقلاص استيل", "اقلاص استيل غير طويل")):
    matches = app.match_products_from_text(query, products)
    names = [str(product.get("name", "")) for product in matches]
    print(query, "=>", names)
    assert expected in names, f"لم يظهر {expected} عند البحث عن {query}"
    product = next(product for product in matches if product.get("name") == expected)
    assert product.get("image_urls"), f"صورة {expected} مفقودة"
print("runtime catalog search test passed")
