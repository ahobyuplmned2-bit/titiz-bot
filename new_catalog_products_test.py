import json
from pathlib import Path
import app


catalog = json.loads(Path("products.json").read_text(encoding="utf-8"))
flask = catalog["ثلاجة أبو قلص الدار الأصلية - ألوان متعددة"]
chopper = catalog["فرامة خضروات مروحية من المائدة"]
containers = catalog["علب حافظات أبو قفل طقم 5 قطع"]
trays = catalog["صياني أكواب 3 حبات"]
gas_spanner = catalog["بانات غاز جهتين أصلية"]
pressure_whistles = catalog["صفيرات ضغط 3 أحجام"]
crown_glasses = catalog["اقلاص التاج الملكي الصغير 6 حبات"]
picnic_basket = catalog["سلال رحلات"]
thermal_bowls = catalog["صحون فرم حراري 3 أحجام"]

assert flask["price"] == "1600"
assert "أبو قلص" in flask["keywords"]
assert "التاج" not in flask["keywords"]
assert "al-dar-tea-flask-cups-1600.jpg" in flask["image_urls"]

assert chopper["price"] == "3000"
assert "فرامة مروحية" in chopper["keywords"]
assert "سرعتين" in chopper["keywords"]
assert "almaeda-fan-chopper-3000.jpg" in chopper["image_urls"]

assert containers["price"] == "1800"
assert "ابو قفل" in containers["keywords"]
assert "5 قطع" in containers["keywords"]
assert "lock-storage-containers-5pcs-1800.jpg" in containers["image_urls"]

assert trays["price"] == "1000"
assert "صياني اكواب" in trays["keywords"]
assert "3 حبات" in trays["keywords"]
assert "tea-cup-trays-3pcs-1000.jpg" in trays["image_urls"]

assert gas_spanner["price"] == "1000"
assert "مفتاح غاز" in gas_spanner["keywords"]
assert "double-ended-gas-spanner-1000.jpg" in gas_spanner["image_urls"]

assert pressure_whistles["price"] == "400"
assert "صفارات ضغط" in pressure_whistles["keywords"]
assert "3 احجام" in pressure_whistles["keywords"]
assert "pressure-cooker-whistles-400.jpg" in pressure_whistles["image_urls"]

assert crown_glasses["price"] == "1000"
assert "اقلاص التاج الملكي" in crown_glasses["keywords"]
assert "6 حبات" in crown_glasses["keywords"]
assert crown_glasses["image_urls"].count("crown-royal-tea-glasses-small-") == 3

assert picnic_basket["price"] == "800"
assert "سلة رحلات" in picnic_basket["keywords"]
assert "picnic-basket-800.jpg" in picnic_basket["image_urls"]

assert thermal_bowls["price"] == "1500"
assert "صحون فرم حراري" in thermal_bowls["keywords"]
assert [(item["name"], item["price"]) for item in thermal_bowls["variants"]] == [
    ("صغير", "1500"),
    ("وسط", "2000"),
    ("كبير", "2500"),
    ("الطقم 3 حبات", "5000"),
]
assert "thermal-serving-bowls-3sizes.jpg" in thermal_bowls["image_urls"]

products = [{"id": index, **data} for index, data in enumerate(catalog.values(), 1)]
flask_matches = app.match_products_from_text("ابو قلص", products)
chopper_matches = app.match_products_from_text("فرامة مروحية", products)
container_matches = app.match_products_from_text("حافظات ابو قفل", products)
tray_matches = app.match_products_from_text("صياني اكواب", products)
gas_spanner_matches = app.match_products_from_text("مفتاح غاز", products)
pressure_whistle_matches = app.match_products_from_text("صفارات ضغط", products)
crown_glasses_matches = app.match_products_from_text("قلاص التاج الملكي", products)
picnic_basket_matches = app.match_products_from_text("سلة رحلات", products)
thermal_bowls_matches = app.match_products_from_text("صحون فرم حراري", products)
assert [item["name"] for item in flask_matches] == [flask["name"]]
assert [item["name"] for item in chopper_matches] == [chopper["name"]]
assert containers["name"] in [item["name"] for item in container_matches]
assert trays["name"] in [item["name"] for item in tray_matches]
assert gas_spanner["name"] in [item["name"] for item in gas_spanner_matches]
assert pressure_whistles["name"] in [item["name"] for item in pressure_whistle_matches]
assert crown_glasses["name"] in [item["name"] for item in crown_glasses_matches]
assert picnic_basket["name"] in [item["name"] for item in picnic_basket_matches]
assert thermal_bowls["name"] in [item["name"] for item in thermal_bowls_matches]

print("new_catalog_products_test: OK")
