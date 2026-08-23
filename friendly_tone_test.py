import app


greeting = app.find_response(app.normalize_text("كيفك"))
assert greeting, "رد التحية يجب أن يبقى موجوداً"
assert "أنا بخير، شكراً لسؤالك" in greeting["reply"]
assert "كيف أقدر أساعدك اليوم؟" in greeting["reply"]

hello = app.find_response(app.normalize_text("هلا"))
assert hello, "رد هلا يجب أن يبقى موجوداً"
assert "كيف أقدر أخدمك اليوم؟" in hello["reply"]

assert "هلا فيكِ في Titiz" in app.WELCOME_MESSAGE
assert "اكتبي اسم المنتج اللي تبغينه" in app.GUIDED_HELP_MESSAGE
assert "حبيت أتأكد عن" not in app.PRODUCT_FOLLOWUP_SATISFIED_MESSAGE

print("friendly_tone_test: OK")
