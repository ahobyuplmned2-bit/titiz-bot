from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "رف زاويه حمام عدن بلستيك الاصلي"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "رف زاويه حمام عدن بلستيك الاصلي": {
    "name": "رف زاويه حمام عدن بلستيك الاصلي",
    "price": "700",
    "description": "رف بلاستيك أصلي عملي لتنظيم الشامبو والصابون والمنظفات في زاوية الحمام، بتصميم خفيف وسهل التنظيف ومناسب للاستخدام اليومي.",
    "keywords": "رف زاويه حمام,رف زاوية حمام,رف حمام عدن,رفوف حمام,رف بلاستيك,رف بلستيك,رف حمام بلاستيك,رف منظفات,رف شامبو,رف صابون,رف زاوية,منظم حمام,منظمات الحمام,رفوف منظفات الوطنية,700 ريال,أدوات حمام,مستلزمات الحمام,تنظيم الحمام",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/bathroom-corner-shelves/aden-plastic-corner-shelf-700.jpg\\"]",
    "variants": ""
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added aden plastic bathroom corner shelf product")
