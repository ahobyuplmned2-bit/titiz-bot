import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["كراسي بلاستيك أبو دنحة أصلية"]

assert product["price"] == "4000"
assert product["variants"] == ""
assert "abu-danha-plastic-chair-4000.jpg" in product["image_urls"]
for keyword in ["كراسي بلاستيك", "أبو دنحة", "كراسي أبو يدين"]:
    assert keyword in product["keywords"]

print("abu_danha_chair_product_test: OK")
