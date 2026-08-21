from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "علب بهارات سلم طويل"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "علب بهارات سلم طويل": {
    "name": "علب بهارات سلم طويل",
    "price": "1700",
    "description": "طقم علب بهارات سلم طويل بتصميم مرتب وألوان عملية لحفظ البهارات والتوابل، مع ملاعق خاصة لكل علبة وقاعدة ثابتة للاستخدام المنزلي الراقي.",
    "keywords": "علب بهارات,علب بهارات سلم,علب بهارات سلم طويل,طقم بهارات,علب توابل,منظم بهارات,علب بهارات بلاستيك,علب بهارات مع قاعدة,علب بهارات ملونة,علب بهارات 6 حبات,1700 ريال,أدوات المطبخ,مستلزمات المطبخ",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/spice-jars/long-spice-jars-clean.png\\"]",
    "variants": ""
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added long spice jars product")
