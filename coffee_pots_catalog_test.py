import json
from pathlib import Path

import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
steel = catalog["جزوات قهوة استيل 3 أحجام"]
tefal = catalog["جزوات تيفال أصلية من المائدة 3 أحجام"]
products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]

assert [variant["price"] for variant in steel["variants"]] == ["500", "1000", "1500"]
assert [variant["price"] for variant in tefal["variants"]] == ["1700", "2000", "2500"]
assert "جزوات استيل" in steel["keywords"]
assert "جزوات تيفال" in tefal["keywords"]
assert "stainless-coffee-pots-3sizes.jpg" in steel["image_urls"]
assert "almaeda-teflon-coffee-pot.jpg" in tefal["image_urls"]

steel_matches = app.match_products_from_text("جزوات استيل", products)
tefal_matches = app.match_products_from_text("جزوات تيفال", products)
assert [item["name"] for item in steel_matches] == [steel["name"]]
assert [item["name"] for item in tefal_matches] == [tefal["name"]]

print("coffee_pots_catalog_test: OK")
