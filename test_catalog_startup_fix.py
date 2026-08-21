from pathlib import Path

source = Path("app.py").read_text(encoding="utf-8")
products_call = source.index("load_products_from_github()")
orders_call = source.index("load_orders_from_github()")
assert products_call < orders_call, "يجب تحميل المنتجات من GitHub قبل استعادة الطلبات"

import json
catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
assert isinstance(catalog, dict) and catalog, "products.json يجب أن يبقى قاموساً غير فارغ"
catalog_names = {str(item.get("name", "")) for item in catalog.values() if isinstance(item, dict)}
for name in ("كفوف غسل", "كفوف صابون", "يدات قدور الضغط", "قدر ضغط ألدار الأصلي (5 سنوات ضمان)"):
    assert name in catalog_names, f"المنتج مفقود من products.json: {name}"

for relative_path in (
    "assets/products/gloves/washing-gloves.jpg",
    "assets/products/gloves/soap-gloves.jpg",
    "assets/products/handles/pressure-cooker-handles.jpg",
    "assets/products/pressure-cookers/aldar-cooker-3-4-5l.jpg",
    "assets/products/pressure-cookers/aldar-cooker-5-7-9l.jpg",
    "assets/products/floor-mops/floor-mop-large-with-handle.jpg",
    "assets/products/floor-mops/floor-mop-medium-with-handle.jpg",
    "assets/products/stove-trivets/square-stove-trivet-1000.jpg",
):
    image_path = Path(relative_path)
    assert image_path.exists() and image_path.stat().st_size > 0, f"صورة المنتج مفقودة: {relative_path}"

mop = catalog.get("موب بلاط مع العصا")
assert isinstance(mop, dict), "سجل موب البلاط مفقود"
assert mop["price"] == "1000", "السعر الأساسي لموب البلاط يجب أن يكون سعر الوسط"
assert "مجنونه مساحه بلاط" in mop["keywords"], "الكلمة المفتاحية باللهجة اليمنية مفقودة"
variants = json.loads(mop["variants"])
assert variants == [{"name": "وسط", "price": 1000}, {"name": "كبير", "price": 1300}], "أحجام موب البلاط أو أسعارها غير صحيحة"
image_urls = json.loads(mop["image_urls"])
assert len(image_urls) == 2, "يجب أن يحتوي موب البلاط على صورتين"

trivet = catalog.get("جلاس شول تمتيك الأصلي المربع (كرسي شول)")
assert isinstance(trivet, dict), "سجل جلاس شول المربع مفقود"
assert trivet["price"] == "1000", "سعر جلاس شول المربع يجب أن يكون 1000"
assert "كرسي شول" in trivet["keywords"], "الكلمة المفتاحية كرسي شول مفقودة"
assert len(json.loads(trivet["image_urls"])) == 1, "يجب أن يحتوي جلاس شول على صورة واحدة"

print("catalog startup and product image regression test passed")
