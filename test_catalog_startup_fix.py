from pathlib import Path

source = Path("app.py").read_text(encoding="utf-8")
products_call = source.index("load_products_from_github()")
orders_call = source.index("load_orders_from_github()")
assert products_call < orders_call, "يجب تحميل المنتجات من GitHub قبل استعادة الطلبات"

import json
catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
assert isinstance(catalog, dict) and catalog, "products.json يجب أن يبقى قاموساً غير فارغ"
catalog_names = {str(item.get("name", "")) for item in catalog.values() if isinstance(item, dict)}
for name in ("كفوف غسل", "كفوف صابون", "يدات قدور الضغط", "قدر ضغط ألدار الأصلي"):
    assert name in catalog_names, f"المنتج مفقود من products.json: {name}"

saifi_star_names = {
    "قلص شاي صيفي ستار الاصلي 6 قطع",
    "قلص شاي صيفي ستار موديل SS-49 6 قطع",
    "قلص شاي صيفي ستار موديل SS-47 6 قطع",
    "قلص شاي صيفي ستار تشكيلة العلبة 6 قطع",
    "قلص شاي صيفي ستار موديل SS-05 6 قطع",
}
assert saifi_star_names <= catalog_names, "يجب أن تبقى تشكيلات صيفي ستار الخمس كسجلات مستقلة"
for name in saifi_star_names:
    product = next(item for item in catalog.values() if item.get("name") == name)
    assert product["price"] == "1400", f"سعر {name} يجب أن يبقى 1400"
    assert len(json.loads(product["image_urls"])) == 1, f"يجب أن يكون لكل تشكيلة صيفي ستار صورة مستقلة"

whisks = catalog.get("مربشة مرابش مجحي")
assert isinstance(whisks, dict), "سجل مربشة مرابش مجحي مفقود"
assert whisks["price"] == "1200", "السعر الأساسي للمضارب يجب أن يكون 1200"
assert json.loads(whisks["variants"]) == [
    {"name": "رقم 1 الكبير", "price": 1200},
    {"name": "رقم 2", "price": 1000},
    {"name": "رقم 3", "price": 800},
    {"name": "رقم 4", "price": 600},
], "مقاسات المضارب أو أسعارها غير صحيحة"
assert "مربشه" in whisks["keywords"] and "مضارب مجحي" in whisks["keywords"], "كلمات المضارب المفتاحية مفقودة"
assert len(json.loads(whisks["image_urls"])) == 1, "يجب أن يحتوي منتج المضارب على صورة واحدة"

pans = catalog.get("حراضي مقالي معدن")
assert isinstance(pans, dict), "سجل حراضي مقالي معدن مفقود"
assert pans["price"] == "600", "السعر الأساسي للحراضي يجب أن يكون 600"
assert json.loads(pans["variants"]) == [
    {"name": "رقم 1 الصغير", "price": 600},
    {"name": "رقم 2", "price": 700},
    {"name": "رقم 3", "price": 900},
    {"name": "رقم 4", "price": 1000},
    {"name": "رقم 5", "price": 1400},
    {"name": "رقم 6", "price": 1700},
], "مقاسات الحراضي أو أسعارها غير صحيحة"
assert "حراضي مقالي" in pans["keywords"] and "مقالي معدن" in pans["keywords"], "كلمات الحراضي المفتاحية مفقودة"
assert len(json.loads(pans["image_urls"])) == 1, "يجب أن يحتوي منتج الحراضي على صورة واحدة"

chinese_stove_eyes = catalog.get("عيون شول صيني")
assert isinstance(chinese_stove_eyes, dict), "سجل عيون شول صيني مفقود"
assert chinese_stove_eyes["price"] == "600", "سعر عيون شول صيني يجب أن يكون 600"
assert "عيون شوال" in chinese_stove_eyes["keywords"], "كلمة عيون شوال المفتاحية مفقودة"
assert len(json.loads(chinese_stove_eyes["image_urls"])) == 1, "يجب أن يحتوي عيون شول صيني على صورة واحدة"

kholani_glasses = catalog.get("اقلاص الخولاني الأصلي 6 قطع")
assert isinstance(kholani_glasses, dict), "سجل اقلاص الخولاني مفقود"
assert kholani_glasses["price"] == "800", "سعر اقلاص الخولاني يجب أن يكون 800"
assert "طقم 6 قطع" in kholani_glasses["keywords"], "كلمة طقم 6 قطع المفتاحية مفقودة"
assert len(json.loads(kholani_glasses["image_urls"])) == 1, "يجب أن يحتوي اقلاص الخولاني على صورة واحدة"

for relative_path in (
    "assets/products/gloves/washing-gloves.jpg",
    "assets/products/gloves/soap-gloves.jpg",
    "assets/products/handles/pressure-cooker-handles.jpg",
    "assets/products/pressure-cookers/aldar-cooker-3-4-5l.jpg",
    "assets/products/pressure-cookers/aldar-cooker-5-7-9l.jpg",
    "assets/products/hindi-storage-containers/dakar-lux-hindi-storage-containers-7pcs.jpg",
    "assets/products/floor-mops/floor-mop-large-with-handle.jpg",
    "assets/products/floor-mops/floor-mop-medium-with-handle.jpg",
    "assets/products/stove-trivets/square-stove-trivet-1000.jpg",
    "assets/products/vegetable-fabric-scissors/original-copper-nut-scissors-800.jpg",
    "assets/products/table-stoves/table-stove-80-m80s-20500.jpg",
    "assets/products/metal-ladles/large-metal-serving-ladle-1400.jpg",
    "assets/products/metal-ladles/large-metal-slotted-ladle-1400.jpg",
    "assets/products/bathroom-corner-shelves/aden-plastic-corner-shelf-700.jpg",
    "assets/products/steel-cups/royal-crown-short-steel-cups.jpg",
    "assets/products/spice-jars/long-spice-jars-clean.png",
    "assets/products/juice-strainers/steel-juice-strainers-with-handles.jpg",
    "assets/products/frying-pans/metal-frying-pans-suitable-background.jpg",
    "assets/products/chinese-stove-eyes/chinese-stove-eyes.jpg",
    "assets/products/tea-cups/kholani-glasses-6pcs.jpg",
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

steel_cups = catalog.get("اقلاص استيل غير طويل")
assert isinstance(steel_cups, dict), "سجل اقلاص الاستيل غير الطويل مفقود"
assert steel_cups["price"] == "300", "السعر الأساسي لاقلاص الاستيل يجب أن يكون سعر الرقم 1 الكبير"
assert "اقلاص استيل" in steel_cups["keywords"] and "التاج الملكي" in steel_cups["keywords"], "كلمات اقلاص الاستيل المفتاحية مفقودة"
steel_cup_variants = json.loads(steel_cups["variants"])
assert steel_cup_variants == [
    {"name": "رقم 1 الكبير", "price": 300},
    {"name": "رقم 2", "price": 250},
    {"name": "رقم 3", "price": 200},
    {"name": "رقم 4", "price": 150},
], "أحجام اقلاص الاستيل أو أسعارها غير صحيحة"
assert len(json.loads(steel_cups["image_urls"])) == 1, "يجب أن يحتوي اقلاص الاستيل على صورة واحدة"

hindi_storage = catalog.get("علب حافظات هندي ابو 7 طقم")
assert isinstance(hindi_storage, dict), "سجل علب حافظات هندي أبو 7 مفقود"
assert hindi_storage["price"] == "1600", "سعر علب حافظات هندي أبو 7 يجب أن يبقى 1600"
assert hindi_storage["image_id"] == "", "يجب إزالة معرّف صورة واتساب المتغير من علب الحافظات"
assert len(json.loads(hindi_storage["image_urls"])) == 1, "يجب أن تحتوي علب الحافظات على رابط صورة ثابت"

spice_jars = catalog.get("علب بهارات سلم طويل")
assert isinstance(spice_jars, dict), "سجل علب بهارات سلم طويل مفقود"
assert spice_jars["price"] == "1700", "سعر علب بهارات سلم طويل يجب أن يكون 1700"
assert "علب بهارات" in spice_jars["keywords"] and "علب بهارات سلم طويل" in spice_jars["keywords"], "كلمات علب البهارات المفتاحية مفقودة"
assert len(json.loads(spice_jars["image_urls"])) == 1, "يجب أن تحتوي علب البهارات على صورة واحدة"

juice_strainers = catalog.get("مشنات استيل عصاير")
assert isinstance(juice_strainers, dict), "سجل مشنات استيل عصاير مفقود"
assert juice_strainers["price"] == "1000", "السعر الأساسي لمشنات العصاير يجب أن يكون سعر الرقم 1 الكبير"
assert "مشنات استيل عصاير" in juice_strainers["keywords"] and "مصفاة عصير" in juice_strainers["keywords"], "كلمات مشنات العصاير المفتاحية مفقودة"
juice_strainer_variants = json.loads(juice_strainers["variants"])
assert juice_strainer_variants == [
    {"name": "رقم 1 الكبير", "price": 1000},
    {"name": "رقم 2 الوسط", "price": 800},
    {"name": "رقم 3 الصغير", "price": 700},
], "أحجام مشنات العصاير أو أسعارها غير صحيحة"
assert len(json.loads(juice_strainers["image_urls"])) == 1, "يجب أن تحتوي مشنات العصاير على صورة واحدة"

print("catalog startup and product image regression test passed")
