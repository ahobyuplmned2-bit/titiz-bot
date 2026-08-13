import app


phrases = [
    "نقصوا لنا",
    "نقص السعر",
    "خفض السعر",
    "في خصم؟",
    "ممكن تخفيض",
    "آخر سعر كم",
    "السعر غالي",
]

for phrase in phrases:
    response = app.find_response(app.normalize_text(phrase))
    assert response is not None, phrase
    assert "أفضل سعر" in response["reply"], phrase
    assert "اسم المنتج" in response["reply"], phrase

assert app.find_response(app.normalize_text("ثلاجة شاي")) is not None
assert app.find_response(app.normalize_text("نقصوا لنا ثلاجة شاي"))["reply"] == app.RESP_DISCOUNT
print("discount_response_test: OK")
