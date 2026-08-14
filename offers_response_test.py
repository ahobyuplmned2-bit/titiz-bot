import app


for phrase in [
    "وين العروض",
    "وين تنزلو العروض",
    "اين العروض",
    "عروضكم وين",
    "عندكم عروض",
    "عروض اليوم",
    "عروض القناة",
    "وين الخصومات",
    "في كوبونات",
    "كود خصم",
    "رابط قناة العروض",
    "Big Save",
]:
    normalized = app.normalize_text(phrase)
    assert app.is_offers_inquiry(normalized), phrase
    assert app.OFFERS_CHANNEL_URL in app.find_response(normalized)["reply"]

assert not app.is_offers_inquiry(app.normalize_text("ثلاجة شاي"))

url_calls = []
app.whatsapp.send_url_button = lambda recipient, text, title, url: url_calls.append(
    (recipient, text, title, url)
) or True
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message(
    "967700000000",
    "وين العروض",
    app.normalize_text("وين العروض"),
    {"type": "text"},
)

assert len(url_calls) == 1
assert app.OFFERS_CHANNEL_URL in url_calls[0][1]
assert url_calls[0][2] == "📞 التواصل مع المندوبة"
assert url_calls[0][3].startswith("https://wa.me/967712282204")
print("offers_response_test: OK")
