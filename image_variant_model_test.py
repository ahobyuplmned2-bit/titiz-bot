import app


pressure_chopper = next(
    product for product in app.get_all_products()
    if "فرامة الضغطة" in product.get("name", "")
)
analysis = {
    "detected_model": "MD-5266",
    "extracted_text": "فرامة الضغطة الذكية MD-5266",
    "matched_product_name": "فرامة الضغطة الذكية من المائدة",
    "visual_description": "فرامة حمراء كبيرة",
}
variant_match = app.resolve_image_variant_match(analysis, pressure_chopper)
assert variant_match is not None
assert variant_match["variant"]["name"] == "الكبير MD-5266"

unknown_model = dict(analysis, detected_model="MD-9999", extracted_text="MD-9999")
assert app.resolve_image_variant_match(unknown_model, pressure_chopper) is None

sent_images = []
sent_buttons = []
app.send_image = lambda to, url, caption="": sent_images.append((to, url, caption)) or True
app.send_image_by_id = lambda to, media_id, caption="": sent_images.append((to, media_id, caption)) or True
app.send_buttons = lambda to, text, buttons: sent_buttons.append((to, text, buttons)) or True
app.schedule_product_followup = lambda *args, **kwargs: None
app.user_states.clear()
app.user_sessions.clear()

app.send_matched_product_variant_card("967700000333", pressure_chopper, variant_match)
assert sent_images
assert sent_buttons
assert "MD-5266" in sent_buttons[0][1]
assert any(button["id"].endswith("_0") for button in sent_buttons[0][2])

print("image_variant_model_test: OK")
