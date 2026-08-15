import app


url_calls = []
fallback = []
app.whatsapp.send_url_button = lambda recipient, text, title, url: url_calls.append(
    (recipient, text, title, url)
) or True
app.send_message = lambda recipient, text: fallback.append((recipient, text))

app.send_unavailable_image_response("967700000444")
assert len(url_calls) == 1
assert url_calls[0][0] == "967700000444"
assert "أرسلنا الصورة مباشرة للإدارة" in url_calls[0][1]
assert url_calls[0][2] == "📞 التواصل مع المندوبة"
assert url_calls[0][3] == app.DELEGATE_WHATSAPP_URL
assert fallback == []

url_calls.clear()
app.whatsapp.send_url_button = lambda *args, **kwargs: False
app.send_unavailable_image_response("967700000445")
assert fallback
assert app.DELEGATE_WHATSAPP_URL in fallback[-1][1]

print("unavailable_image_response_test: OK")
