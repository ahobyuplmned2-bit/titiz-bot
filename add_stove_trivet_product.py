from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "جلاس شول تمتيك الأصلي المربع (كرسي شول)"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "جلاس شول تمتيك الأصلي المربع (كرسي شول)": {
    "name": "جلاس شول تمتيك الأصلي المربع (كرسي شول)",
    "price": "1000",
    "description": "قاعدة شول مربعة أصلية وثابتة، تساعد على تثبيت القدور والأواني فوق عين الغاز وتوزيع الحرارة بشكل عملي للاستخدام اليومي في المطبخ.",
    "keywords": "جلاس شول,جلاس شولة,جلاس شول تمتيك,جلاس شول تمتك,كرسي شول,كرسي شولة,قاعدة شول,قاعدة شولة,حامل قدر,حامل القدر,حامل أواني,قاعدة غاز,قاعدة عين الغاز,جلاس مربع,شول مربع,شولة مربع,جلاس شول اصلي,جلاس شول أصلي,تمتيك,1000 ريال,أدوات مطبخ,مستلزمات الغاز",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/stove-trivets/square-stove-trivet-1000.jpg\\"]",
    "variants": ""
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added square stove trivet product")
