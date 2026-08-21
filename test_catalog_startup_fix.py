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
):
    image_path = Path(relative_path)
    assert image_path.exists() and image_path.stat().st_size > 0, f"صورة المنتج مفقودة: {relative_path}"

print("catalog startup and product image regression test passed")
