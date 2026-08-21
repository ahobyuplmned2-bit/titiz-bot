from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "مشنات استيل عصاير"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "مشنات استيل عصاير": {
    "name": "مشنات استيل عصاير",
    "price": "1000",
    "description": "مشنات استيل أصلية بعصا ومقبض خشبي، مناسبة لتصفية العصائر والمشروبات والطبخ، ومتوفرة بثلاثة أحجام للاستخدام اليومي.",
    "keywords": "مشنات استيل عصاير,مشنات عصاير,مصفاة عصير,مصفاة عصاير استيل,مشن استيل,مشنات استيل اصلية,مشنات بعصا,مصفاة بعصا,مصفاة مشروبات,مصفاة مطبخ,مصفاة كبيرة,مصفاة وسط,مصفاة صغيرة,أدوات عصائر,أدوات مطبخ,مستلزمات المطبخ,التاج الملكي,1000 ريال,800 ريال,700 ريال",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/juice-strainers/steel-juice-strainers-with-handles.png\\"]",
    "variants": "[{\\"name\\": \\"رقم 1 الكبير\\", \\"price\\": 1000}, {\\"name\\": \\"رقم 2 الوسط\\", \\"price\\": 800}, {\\"name\\": \\"رقم 3 الصغير\\", \\"price\\": 700}]"
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added steel juice strainers product")
