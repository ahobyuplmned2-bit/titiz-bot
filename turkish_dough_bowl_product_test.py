import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["عيشات تركي طوات عجين صغيرة"]

assert product["price"] == "600"
assert product["variants"] == ""
assert "small-turkish-dough-bowl-600.jpg" in product["image_urls"]
for keyword in ["عيشات تركي", "طوات عجين", "حافظة خبز"]:
    assert keyword in product["keywords"]

print("turkish_dough_bowl_product_test: OK")
