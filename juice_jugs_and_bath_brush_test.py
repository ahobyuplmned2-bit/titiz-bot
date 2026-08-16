import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

jugs = catalog["جاكات عصير أبو حزام مع 4 اقلاص"]
assert jugs["price"] == "1800"
assert "juice-jugs-abu-hizam-1.jpg" in jugs["image_urls"]
assert "juice-jugs-abu-hizam-2.jpg" in jugs["image_urls"]
for keyword in ["جاكات عصير", "أبو حزام", "4 اقلاص"]:
    assert keyword in jugs["keywords"]

brush = catalog["فرشاة حمام جهتين أبو عصا استيل أصلية"]
assert brush["price"] == "500"
assert "double-sided-stainless-handle-bath-brush-500.jpg" in brush["image_urls"]
for keyword in ["برشات حمام", "أبو عصا", "عصا استيل"]:
    assert keyword in brush["keywords"]

print("juice_jugs_and_bath_brush_test: OK")
