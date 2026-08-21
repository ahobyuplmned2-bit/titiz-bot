from pathlib import Path

catalog_path = Path("products.json")
text = catalog_path.read_text(encoding="utf-8")
key = '  "موب بلاط مع العصا"'
if key in text:
    raise SystemExit("المنتج موجود مسبقاً؛ لم يتم تعديل products.json")

entry = '''  "موب بلاط مع العصا": {
    "name": "موب بلاط مع العصا",
    "price": "1000",
    "description": "ممسحة بلاط عملية مع عصا، مناسبة لتنظيف الأرضيات والبلاط وإزالة الماء والأوساخ بسهولة. متوفرة بحجم وسط وكبير للاستخدام المنزلي.",
    "keywords": "موب بلاط,موب بلاط مع العصا,موب بلاط كبير,موب بلاط وسط,ممسحة بلاط,مساحة بلاط,مجنونه مساحه بلاط,ممسحة أرضيات,مساحة أرضيات,ممسحة تنظيف,مساحة تنظيف,تنظيف البلاط,تنظيف الأرضيات,مسح البلاط,مسح الأرض,عصا موب,موب بعصا,ممسحة مع عصا,كبير,وسط,1000 ريال,1300 ريال,أدوات تنظيف,مستلزمات المنزل",
    "image_id": "",
    "image_urls": "[\\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/floor-mops/floor-mop-large-with-handle.jpg\\", \\"https://raw.githubusercontent.com/ahobyuplmned2-bit/titiz-bot/main/assets/products/floor-mops/floor-mop-medium-with-handle.jpg\\"]",
    "variants": "[{\\"name\\": \\"وسط\\", \\"price\\": 1000}, {\\"name\\": \\"كبير\\", \\"price\\": 1300}]"
  }
'''
closing = "\n}"
if not text.endswith(closing):
    raise SystemExit("صيغة products.json غير متوقعة؛ لم يتم التعديل")
catalog_path.write_text(text[:-len(closing)] + ",\n" + entry + "}", encoding="utf-8")
print("added floor mop product")
