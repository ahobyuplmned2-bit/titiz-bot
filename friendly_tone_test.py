import app


expected_how_are_you_reply = (
    "أنا بخير وبأتم الاستعداد لمساعدتك! شكرًا لسؤالك.\n\n"
    "بصفتي مساعدك في Titiz، يمكنني مساعدتك في العثور على أفضل المنتجات بل جملة وتجزئة. "
    "كيف يمكنني خدمتك اليوم؟ هل تبحث عن منتج معين؟"
)
for phrase in ("كيفك", "كيف الحال"):
    greeting = app.find_response(app.normalize_text(phrase))
    assert greeting, f"رد التحية يجب أن يبقى موجوداً لعبارة: {phrase}"
    assert greeting["reply"] == expected_how_are_you_reply

hello = app.find_response(app.normalize_text("هلا"))
assert hello, "رد هلا يجب أن يبقى موجوداً"
assert "كيف أقدر أخدمك اليوم؟" in hello["reply"]

assert "هلا فيك" in app.WELCOME_MESSAGE
assert "اكتب اسم المنتج اللي تبغاه" in app.GUIDED_HELP_MESSAGE
assert "حبيت أتأكد عن" not in app.PRODUCT_FOLLOWUP_SATISFIED_MESSAGE

print("friendly_tone_test: OK")
