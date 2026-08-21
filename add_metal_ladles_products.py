from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
entries = [
    '''  "ملاعق معدن غرف كبير": {
    "name": "ملاعق معدن غرف كبير",
    "price": "1400",
    "description": "ملاعق غرف كبيرة من المعدن، مناسبة لغرف الشوربة والمرق والطعام وتقديمه بسهولة. عبوة كبيرة عملية للاستخدام اليومي في المطبخ.",
    "keywords": "ملاعق معدن غرف,ملاعق معدن غرف كبير,ملعقة غرف كبيرة,ملاعق غرف كبيرة,ملاعق شوربة معدن,ملاعق مرق,ملاعق تقديم,ملاعق مطبخ معدن,ملاعق استيل,ملاعق ستيل,ملاعق كبيرة,عبوة 60,عدد 60,1400 ريال,أدوات مطبخ,مستلزمات المطبخ",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/metal-ladles/large-metal-serving-ladle-1400.jpg\\"]",
    "variants": ""
  }''',
    '''  "ملاعق مشن معدن كبير": {
    "name": "ملاعق مشن معدن كبير",
    "price": "1400",
    "description": "ملاعق مشن كبيرة من المعدن، مثقبة لتصفية الطعام والزيت والماء، مناسبة للقلي والطبخ وتقديم الأطعمة. عبوة كبيرة للاستخدام المنزلي.",
    "keywords": "ملاعق مشن,ملاعق مشن معدن,ملاعق مشن معدن كبير,ملعقة مشن كبيرة,ملاعق مثقبة,ملاعق مصفاة,ملاعق قلي,ملاعق تصفية,ملاعق تقديم معدن,ملاعق استيل,ملاعق ستيل,ملاعق كبيرة,عبوة 60,عدد 60,1400 ريال,أدوات مطبخ,مستلزمات المطبخ",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/metal-ladles/large-metal-slotted-ladle-1400.jpg\\"]",
    "variants": ""
  }'''
]
for name in ("ملاعق معدن غرف كبير", "ملاعق مشن معدن كبير"):
    if f'  "{name}"' in text:
        raise SystemExit(f"المنتج موجود مسبقاً: {name}")
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
text = text[:-len(closing)] + ",\n" + ",\n".join(entries) + "\n}"
catalog_path.write_text(text, encoding="utf-8")
print("added metal ladle products")
