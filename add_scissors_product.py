from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "مقصات خضار وقماش الأصلي ضمان نحاس"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "مقصات خضار وقماش الأصلي ضمان نحاس": {
    "name": "مقصات خضار وقماش الأصلي ضمان نحاس",
    "price": "800",
    "description": "مقصات أصلية قوية ومناسبة لتقطيع الخضار وقص القماش والاستخدامات المنزلية المتعددة، بتصميم متين وصامولة نحاس، مع ضمان.",
    "keywords": "مقصات خضار,مقص خضار,مقصات قماش,مقص قماش,مقصات المطبخ,مقص مطبخ,مقصات منزلية,مقص منزلي,مقص صاموله نحاس,مقص صامولة نحاس,صاموله نحاس,صامولة نحاس,مقص نحاس,مقص أصلي,مقص اصلي,مقص بضمان,ضمان,قص الخضار,قص القماش,800 ريال,أدوات مطبخ,أدوات منزلية",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/vegetable-fabric-scissors/original-copper-nut-scissors-800.jpg\\"]",
    "variants": ""
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added vegetable and fabric scissors product")
