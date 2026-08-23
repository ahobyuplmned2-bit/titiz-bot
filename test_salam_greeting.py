import app


EXPECTED_REPLY = (
    "وعليكم السلام ورحمة الله وبركاته! كيف يمكنني مساعدتك اليوم في رحلة البحث "
    "الخاصة بك عبر Titiz؟ سواء كنت تبحث عن منتجات جديدة ومحلات موثوقين، أنا هنا لخدمتك."
)

for greeting in ("السلام", "السلام عليكم", "السلام وعليكم"):
    response = app.find_response(app.normalize_text(greeting))
    assert response, f"يجب أن يوجد رد لعبارة: {greeting}"
    assert response["reply"] == EXPECTED_REPLY, f"رد السلام غير مطابق لعبارة: {greeting}"

print("test_salam_greeting: OK")
