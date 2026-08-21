import tempfile
from pathlib import Path

import database

import app

original_db_path = database.DB_PATH
original_github_load = app.github_load
with tempfile.TemporaryDirectory() as temp_dir:
    database.DB_PATH = str(Path(temp_dir) / "fallback_catalog.db")
    database.init_db()
    app.github_load = lambda filename: ({}, "")
    app.load_products_from_github()
    products = {product["name"]: product for product in database.get_all_products()}
    assert "مشنات استيل عصاير" in products, "fallback لم يحمّل المشنات"
    assert "اقلاص استيل غير طويل" in products, "fallback لم يحمّل الاقلاص"
    assert products["مشنات استيل عصاير"]["variants"]
    assert products["اقلاص استيل غير طويل"]["image_urls"]

app.github_load = original_github_load
database.DB_PATH = original_db_path
print("catalog local fallback test passed")
