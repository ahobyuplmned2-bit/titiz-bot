import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

corner = catalog["زوايا حمام استيل 2 و3 رفوف"]
assert corner["price"] == "2500"
assert [(item["name"], item["price"]) for item in corner["variants"]] == [
    ("2 رفوف", "2500"),
    ("3 رفوف", "3000"),
]
assert "stainless-bathroom-corner-shelves-2-3.jpg" in corner["image_urls"]

toilet_brush = catalog["فرش حمام أبو قاعدة"]
assert toilet_brush["price"] == "800"
assert "toilet-brush-with-base-800.jpg" in toilet_brush["image_urls"]
assert "أبو قاعدة" in toilet_brush["keywords"]

sink_strainer = catalog["مشنات مغاسل بلاستيك"]
assert sink_strainer["price"] == "800"
assert "plastic-sink-strainer-800.jpg" in sink_strainer["image_urls"]
for keyword in ["مشنات مغاسل", "شبك مغاسل", "مصفاة حوض"]:
    assert keyword in sink_strainer["keywords"]

print("bathroom_and_sink_products_test: OK")
