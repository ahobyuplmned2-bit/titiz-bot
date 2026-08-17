import json
from pathlib import Path


catalog = json.loads(Path(__file__).with_name("products.json").read_text(encoding="utf-8"))
product = catalog["خلاط بهارات كهربائي أصلي المائدة"]

assert product["price"] == "2500"
assert "original-electric-spice-grinder-2500.jpg" in product["image_urls"]
for keyword in ["خلاط بهارات", "مطحنة بهارات", "خلاط بن", "المائدة", "2500 ريال"]:
    assert keyword in product["keywords"]

print("electric_spice_grinder_product_test: OK")
