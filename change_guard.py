"""حارس تغييرات الكتالوج: يرفض تغيير منتجات غير مأذون بها قبل الرفع."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
CATALOG_PATH = PROJECT / "products.json"


def read_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("products.json يجب أن يكون قاموس منتجات")
    return data


def catalog_from_git(ref: str) -> dict:
    raw = subprocess.check_output(
        ["git", "show", f"{ref}:products.json"],
        cwd=PROJECT,
        text=True,
    )
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("نسخة الكتالوج المرجعية غير صالحة")
    return data


def changed_products(before: dict, after: dict) -> set[str]:
    keys = set(before) | set(after)
    return {key for key in keys if before.get(key) != after.get(key)}


def validate_product_schema(catalog: dict) -> list[str]:
    issues = []
    for key, product in catalog.items():
        if not isinstance(product, dict):
            issues.append(f"{key}: سجل المنتج ليس كائناً")
            continue
        if not str(product.get("name") or "").strip():
            issues.append(f"{key}: اسم المنتج فارغ")
        if not str(product.get("price") or "").strip():
            issues.append(f"{key}: السعر فارغ")
        if not product.get("image_urls") and not product.get("image_id"):
            issues.append(f"{key}: لا توجد صورة أو معرّف وسائط")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="يتحقق من أن تعديل الكتالوج يقتصر على المنتجات المأذون بها")
    parser.add_argument("--base", default="HEAD", help="مرجع Git قبل التعديل، الافتراضي HEAD")
    parser.add_argument(
        "--allow-product",
        action="append",
        default=[],
        help="اسم مفتاح المنتج المأذون بتعديله؛ يكرر عند الحاجة",
    )
    args = parser.parse_args()

    try:
        before = catalog_from_git(args.base)
        after = read_catalog(CATALOG_PATH)
    except Exception as exc:
        print(f"CHANGE GUARD FAILED: تعذر قراءة الكتالوج: {exc}")
        return 2

    schema_issues = validate_product_schema(after)
    if schema_issues:
        print("CHANGE GUARD FAILED: أخطاء بنية الكتالوج")
        for issue in schema_issues:
            print(f"- {issue}")
        return 2

    changed = changed_products(before, after)
    allowed = set(args.allow_product)
    unauthorized = changed - allowed
    if unauthorized:
        print("CHANGE GUARD BLOCKED: منتجات تغيرت دون إذن صريح")
        for name in sorted(unauthorized):
            print(f"- {name}")
        return 1

    print(
        "CHANGE GUARD OK: "
        f"تغير {len(changed)} منتجاً، وكلها ضمن المنتجات المأذون بها."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
