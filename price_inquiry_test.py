import app


for phrase in [
    "بكم",
    "بكم هذا",
    "كم السعر",
    "السعر كم",
    "كم حقها",
    "بكم تبيعوا",
    "كم قيمة المنتج",
]:
    normalized = app.normalize_text(phrase)
    assert app.is_price_inquiry(normalized), phrase
    assert "أسعارنا مخفّضة" in app.find_response(normalized)["reply"]

assert not app.is_price_inquiry(app.normalize_text("ثلاجة شاي"))
assert app.DELEGATE_WHATSAPP_URL.startswith("https://wa.me/967712282204")

url_calls = []
app.whatsapp.send_url_button = lambda recipient, text, title, url: url_calls.append(
    (recipient, text, title, url)
) or True
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message(
    "967700000000",
    "بكم",
    app.normalize_text("بكم"),
    {"type": "text"},
)

assert len(url_calls) == 1
assert url_calls[0][2] == "📞 التواصل مع المندوبة"
assert url_calls[0][3].startswith("https://wa.me/967712282204")
assert "أسعارنا مخفّضة" in url_calls[0][1]
print("price_inquiry_test: OK")
