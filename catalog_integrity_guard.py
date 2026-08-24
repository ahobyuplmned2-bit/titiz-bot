"""فحص مرجعي يمنع اختفاء المنتجات والتشكيلات المحمية قبل رفع البوت."""

import json
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
CATALOG_PATH = PROJECT / "products.json"

# هذا الحد هو عدد المنتجات عند تثبيت الحماية. يمكن زيادة العدد عند إضافة منتجات
# مأذون بها، لكن انخفاضه يعني أن سجلاً اختفى ويجب إيقاف الرفع.
MINIMUM_PRODUCT_COUNT = 98

PROTECTED_GROUPS = {
    "تشكيلات اقلاص شاي صيفي ستار": {
        "price": "1400",
        "products": {
            "قلص شاي صيفي ستار الاصلي 6 قطع": "ss33.png",
            "قلص شاي صيفي ستار موديل SS-49 6 قطع": "ss49.png",
            "قلص شاي صيفي ستار موديل SS-47 6 قطع": "ss47.png",
            "قلص شاي صيفي ستار تشكيلة العلبة 6 قطع": "tea-set-box.jpg",
            "قلص شاي صيفي ستار موديل SS-05 6 قطع": "ss05.jpg",
        },
    },
    "مربشة مرابش مجحي": {
        "price": "1200",
        "products": {
            "مربشة مرابش مجحي": "stainless-whisks-suitable-background.jpg",
        },
    },
    "حراضي مقالي معدن": {
        "price": "600",
        "products": {
            "حراضي مقالي معدن": "metal-frying-pans-suitable-background.jpg",
        },
    },
    "عيون شول صيني": {
        "price": "600",
        "products": {
            "عيون شول صيني": "chinese-stove-eyes.jpg",
        },
    },
    "اقلاص الخولاني الأصلي": {
        "price": "800",
        "products": {
            "اقلاص الخولاني الأصلي 6 قطع": "kholani-glasses-6pcs.jpg",
        },
    },
    "منظم غاز إيطالي أصلي": {
        "price": "2000",
        "products": {
            "منظم غاز إيطالي أصلي (ساعة غاز)": "italian-gas-regulator-5y.jpg",
        },
    },
    "علب بهارات أبو 9 مع 3 رفوف": {
        "price": "2800",
        "products": {
            "علب بهارات أبو 9 مع 3 رفوف": "spice-jars-9-with-3-racks.jpg",
        },
    },
    "مكانس تركي ريش رطب": {
        "price": "1200",
        "products": {
            "مكانس تركي ريش رطب": "turkish-wet-bristle-brooms.jpg",
        },
    },
    "سلك غسيل أبو مقبض الأصلي": {
        "price": "300",
        "products": {
            "سلك غسيل أبو مقبض الأصلي": "original-handled-scouring-pad.jpg",
        },
    },
}


def read_catalog(path: Path = CATALOG_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("products.json يجب أن يكون قاموساً")
    return data


def image_urls(product: dict) -> list[str]:
    raw = product.get("image_urls") or ""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    return raw if isinstance(raw, list) else []


def validate_catalog(catalog: dict) -> list[str]:
    issues = []
    if len(catalog) < MINIMUM_PRODUCT_COUNT:
        issues.append(
            f"عدد المنتجات انخفض إلى {len(catalog)}؛ الحد المحمي هو {MINIMUM_PRODUCT_COUNT}"
        )

    for group_name, group in PROTECTED_GROUPS.items():
        for name, expected_image_part in group["products"].items():
            product = catalog.get(name)
            if not isinstance(product, dict):
                issues.append(f"{group_name}: التشكيلة مفقودة: {name}")
                continue
            if str(product.get("price")) != group["price"]:
                issues.append(f"{group_name}: سعر {name} تغيّر عن {group['price']}")
            urls = image_urls(product)
            if len(urls) != 1 or expected_image_part not in str(urls[0]):
                issues.append(f"{group_name}: صورة {name} غير موجودة أو تغيّرت")

    return issues


def main() -> int:
    try:
        issues = validate_catalog(read_catalog())
    except Exception as exc:
        print(f"CATALOG INTEGRITY FAILED: تعذر قراءة الكتالوج: {exc}")
        return 2
    if issues:
        print("CATALOG INTEGRITY BLOCKED: اكتُشف اختفاء أو تغيير محمي")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(
        "CATALOG INTEGRITY OK: "
        f"{len(read_catalog())} منتجاً، وتشكيلات صيفي ستار الخمس والمنتجات الحديثة المحمية محفوظة."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
