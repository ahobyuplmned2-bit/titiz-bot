import app


product = {
    "id": 991001,
    "name": "منتج اختبار للمشاركة",
    "price": "1800",
    "description": "وصف المنتج الجاهز للنشر",
    "keywords": "اختبار",
    "image_id": "",
    "image_urls": "",
    "variants": "",
}

sent = []
app.send_image_by_id = lambda to, image_id, caption: sent.append(("image", to, image_id, caption)) or True
app.send_image = lambda to, image_url, caption: sent.append(("url", to, image_url, caption)) or True
app.send_message = lambda to, text: sent.append(("text", to, text)) or True
app.canonicalize_product = lambda item: item
app._product_image_urls = lambda item: []

assert app.send_admin_share_card(product, image_id="media-admin-card")
assert len(sent) == 1
kind, target, media_id, caption = sent[0]
assert kind == "image"
assert target == app.OWNER_NUMBER
assert media_id == "media-admin-card"
assert "بطاقة جاهزة للنشر" in caption
assert "منتج اختبار للمشاركة" in caption
assert "1800" in caption
assert "شارك" in caption

print("admin_share_card_test: OK")
