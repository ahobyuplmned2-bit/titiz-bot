from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "شوله المائده رقم80"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "شوله المائده رقم80": {
    "name": "شوله المائده رقم80",
    "price": "20500",
    "description": "شولة مائدة المائدة الأصلية رقم 80 من M80S، بثلاث عيون وبدن استيل عملي، مناسبة للطبخ اليومي في المنزل، مع إشعال غاز ثابت وتصميم سهل التنظيف.",
    "keywords": "شوله المائده,شولة المائدة,شوله الماده,شولة الماده,طباخه المائده,طباخة المائدة,طباخه الماده,طباخة الماده,شوله رقم 80,شولة رقم 80,رقم80,M80S,M80,شوله ثلاث عيون,شولة 3 عيون,شوله 3عيون,شولة غاز,طباخة غاز,شوله استيل,شولة استيل,شوله اصلي,شولة أصلي,شولة المائدة الأصلي,شوله ضمان,20500 ريال,20 الف و500,أدوات مطبخ,مستلزمات المطبخ",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/table-stoves/table-stove-80-m80s-20500.jpg\\"]",
    "variants": ""
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added table stove 80 product")
