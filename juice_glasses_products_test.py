import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))

pineapple = catalog["اقلاص عصير أناناس 6 حبات"]
assert pineapple["price"] == "1500"
assert pineapple["variants"] == ""
assert "pineapple-juice-glasses-6pcs-1500.jpg" in pineapple["image_urls"]
for keyword in ["اقلاص عصير أناناس", "اناناس", "6 حبات"]:
    assert keyword in pineapple["keywords"]

hexagonal = catalog["اقلاص عصير طويل سداسي كبير"]
assert hexagonal["price"] == "1700"
assert hexagonal["variants"] == ""
assert "large-hexagonal-juice-glass-1700.jpg" in hexagonal["image_urls"]
for keyword in ["اقلاص عصير طويل", "سداسي", "كبير"]:
    assert keyword in hexagonal["keywords"]

print("juice_glasses_products_test: OK")
