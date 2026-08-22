import database
import app

# التأكد من تحميل الكتالوج محلياً وقاعدة البيانات
database.init_db()
app.load_products_from_github()

products = database.get_all_products()
print("إجمالي المنتجات في قاعدة البيانات:", len(products))

for query in ("مشنات استيل", "اقلاص استيل", "مشنات"):
    normalized = app.normalize_text(query)
    matches = app.match_products_from_text(query, products)
    print(f"استعلام: '{query}' => مطابقات الكتالوج: {[p['name'] for p in matches]}")
    assert len(matches) > 0, f"لا توجد مطابقات للاستعلام: {query}"

print("customer search simulation test passed")
