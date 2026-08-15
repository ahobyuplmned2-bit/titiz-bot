import json
from pathlib import Path


root = Path(__file__).resolve().parent
catalog = json.loads((root / "products.json").read_text(encoding="utf-8"))
source = (root / "app.py").read_text(encoding="utf-8")

assert "ثلاجة شاي أصلية من المائدة 0.7 لتر" not in catalog
assert "M213" not in source
assert "تحفظ الحرارة 6 ساعات" not in source
assert any("ثلاجات شاي التاج الملكي" in name for name in catalog)

print("m213_removal_test: OK")
