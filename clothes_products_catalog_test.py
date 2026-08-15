import json
from pathlib import Path

import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
pegs = catalog["مسكات ملابس وثياب أصلية 10 حبات"]
hangers = catalog["علاقات ملابس استيل جاوي 10 حبات"]
products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]

assert pegs["price"] == "300"
assert "مشابك غسيل" in pegs["keywords"]
assert "clothes-pegs-10pcs-300.jpg" in pegs["image_urls"]
assert hangers["price"] == "1200"
assert "علاقات استيل" in hangers["keywords"]
assert "stainless-clothes-hangers-10pcs-1200.jpg" in hangers["image_urls"]

peg_matches = app.match_products_from_text("مسكات غسيل", products)
hanger_matches = app.match_products_from_text("علاقات استيل", products)
assert [item["name"] for item in peg_matches] == [pegs["name"]]
assert [item["name"] for item in hanger_matches] == [hangers["name"]]

print("clothes_products_catalog_test: OK")
