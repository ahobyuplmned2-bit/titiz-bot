from whatsapp_api import format_product_card


almaeda = {
    "name": "ثلاجة شاي أصلية من المائدة 0.7 لتر",
    "price": "2500",
    "description": "ثلاجة شاي أصلية من المائدة بسعة 0.7 لتر، حافظة للحرارة ومناسبة للشاي والمشروبات الساخنة، ومتوفرة بألوان متعددة.",
    "quantity": 100,
    "variants": "",
}

crown = {
    "name": "ثلاجات شاي التاج الملكي بضمان من أي تبريد",
    "price": "2500",
    "description": "ثلاجات شاي التاج الملكي الأصلية بضمان من أي تبريد، حافظة للحرارة ومتوفرة بأربع سعات مناسبة للشاي والمشروبات الساخنة.",
    "quantity": 100,
    "variants": [
        {"name": "1.0 لتر", "price": "2500"},
        {"name": "1.3 لتر", "price": "3000"},
        {"name": "1.6 لتر", "price": "3500"},
        {"name": "1.9 لتر", "price": "4000"},
    ],
}

almaeda_card = format_product_card(almaeda, compact=True)
crown_card = format_product_card(crown, compact=True)
assert "2500" in almaeda_card
assert "2500" in crown_card and "3000" in crown_card and "3500" in crown_card and "4000" in crown_card
assert len(almaeda_card) <= 160
assert len(crown_card) <= 160
assert format_product_card(almaeda).count("2500") == 1
print("tea_price_card_test: OK")
print(almaeda_card)
print(crown_card)
