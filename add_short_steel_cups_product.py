from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "اقلاص استيل غير طويل"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "اقلاص استيل غير طويل": {
    "name": "اقلاص استيل غير طويل",
    "price": "300",
    "description": "اقلاص استيل أصلي من التاج الملكي، تصميم غير طويل ومتين مناسب للماء والعصائر والاستخدام اليومي. متوفر بأربعة أرقام وأحجام مختلفة.",
    "keywords": "اقلاص استيل,أقلاص استيل,كاسات استيل,كاسات ستيل,اقلاص غير طويل,أقلاص غير طويل,كاسات غير طويلة,اقلاص التاج الملكي,أقلاص التاج الملكي,التاج الملكي,اقلاص رقم 1,اقلاص رقم1,اقلاص رقم 2,اقلاص رقم2,اقلاص رقم 3,اقلاص رقم3,اقلاص رقم 4,اقلاص رقم4,كبير,وسط,صغير,أكواب استيل,أكواب ستيل,300 ريال,250 ريال,200 ريال,150 ريال,أدوات مائدة,مستلزمات المطبخ",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/steel-cups/royal-crown-short-steel-cups.jpg\\"]",
    "variants": "[{\\"name\\": \\"رقم 1 الكبير\\", \\"price\\": 300}, {\\"name\\": \\"رقم 2\\", \\"price\\": 250}, {\\"name\\": \\"رقم 3\\", \\"price\\": 200}, {\\"name\\": \\"رقم 4\\", \\"price\\": 150}]"
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added short steel cups product")
