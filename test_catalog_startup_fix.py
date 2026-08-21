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
    "assets/products/vegetable-fabric-scissors/original-copper-nut-scissors-800.jpg",
    "assets/products/table-stoves/table-stove-80-m80s-20500.jpg",
    "assets/products/metal-ladles/large-metal-serving-ladle-1400.jpg",
    "assets/products/metal-ladles/large-metal-slotted-ladle-1400.jpg",
    "assets/products/bathroom-corner-shelves/aden-plastic-corner-shelf-700.jpg",
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

scissors = catalog.get("مقصات خضار وقماش الأصلي ضمان نحاس")
assert isinstance(scissors, dict), "سجل المقصات مفقود"
assert scissors["price"] == "800", "سعر المقصات يجب أن يكون 800"
assert "مقصات خضار" in scissors["keywords"] and "مقصات قماش" in scissors["keywords"], "كلمات المقصات المفتاحية مفقودة"
assert len(json.loads(scissors["image_urls"])) == 1, "يجب أن يحتوي منتج المقصات على صورة واحدة"

table_stove = catalog.get("شوله المائده رقم80")
assert isinstance(table_stove, dict), "سجل شولة المائدة رقم 80 مفقود"
assert table_stove["price"] == "20500", "سعر شولة المائدة رقم 80 يجب أن يكون 20500"
assert "M80S" in table_stove["keywords"] and "شولة 3 عيون" in table_stove["keywords"], "كلمات شولة المائدة المفتاحية مفقودة"
assert len(json.loads(table_stove["image_urls"])) == 1, "يجب أن يحتوي منتج شولة المائدة على صورة واحدة"

serving_ladle = catalog.get("ملاعق معدن غرف كبير")
assert isinstance(serving_ladle, dict), "سجل ملاعق معدن غرف كبير مفقود"
assert serving_ladle["price"] == "1400", "سعر ملاعق غرف يجب أن يكون 1400"
assert "ملاعق معدن غرف" in serving_ladle["keywords"], "كلمات ملاعق غرف المفتاحية مفقودة"
assert len(json.loads(serving_ladle["image_urls"])) == 1, "يجب أن يحتوي منتج ملاعق غرف على صورة واحدة"

slotted_ladle = catalog.get("ملاعق مشن معدن كبير")
assert isinstance(slotted_ladle, dict), "سجل ملاعق مشن معدن كبير مفقود"
assert slotted_ladle["price"] == "1400", "سعر ملاعق مشن يجب أن يكون 1400"
assert "ملاعق مشن" in slotted_ladle["keywords"], "كلمات ملاعق مشن المفتاحية مفقودة"
assert len(json.loads(slotted_ladle["image_urls"])) == 1, "يجب أن يحتوي منتج ملاعق مشن على صورة واحدة"

bathroom_shelf = catalog.get("رف زاويه حمام عدن بلستيك الاصلي")
assert isinstance(bathroom_shelf, dict), "سجل رف زاوية حمام عدن مفقود"
assert bathroom_shelf["price"] == "700", "سعر رف الحمام يجب أن يكون 700"
assert "رف زاويه حمام" in bathroom_shelf["keywords"] and "رف بلاستيك" in bathroom_shelf["keywords"], "كلمات رف الحمام المفتاحية مفقودة"
assert len(json.loads(bathroom_shelf["image_urls"])) == 1, "يجب أن يحتوي رف الحمام على صورة واحدة"

print("catalog startup and product image regression test passed")
