import app


sent = []
app.send_message = lambda recipient, text: sent.append((recipient, text))
app.send_list = lambda recipient, body, button_text, sections: sent.append((recipient, body, button_text, sections))
app.send_buttons = lambda recipient, text, buttons: sent.append((recipient, text, buttons))
app.send_welcome = lambda recipient: sent.append((recipient, "welcome"))
app.send_product_card = lambda recipient, product: sent.append((recipient, product.get("name")))
app.send_cart_view = lambda recipient: sent.append((recipient, "cart"))
app.cancel_customer_followup = lambda recipient: None
app.whatsapp.send_url_button = lambda recipient, text, title, url: sent.append((recipient, title, url)) or True

assert app.route_semantic_intent(
    "967700000000",
    "ههههه",
    {"intent": "social_chat", "reply": "ههههه منورة 😊 كيف أساعدك؟"},
    [],
)
assert "منورة" in sent[-1][1]
assert sent[-1][2] == "اختاري الخدمة"
assert {row["id"] for row in sent[-1][3][0]["rows"]} >= {
    "menu_search", "menu_cart", "menu_orders", "menu_offers", "menu_contact"
}

assert app.route_semantic_intent(
    "967700000000",
    "لا تذكريني",
    {"intent": "stop_reminder", "reply": ""},
    [],
)
assert sent[-1][1].startswith("✅ تم إيقاف")

assert app.route_semantic_intent(
    "967700000000",
    "أريد أكلم مندوبة",
    {"intent": "agent_handoff", "reply": ""},
    [],
)
assert sent[-1][1] == "📞 التواصل مع المندوبة"

assert app.route_semantic_intent(
    "967700000000",
    "أحتاج شيء رخيص",
    {"intent": "budget", "reply": "أبشري، كم ميزانيتك؟"},
    [],
)
assert "ميزانيتك" in sent[-1][1]

phone = "967700000001"
app.user_states.pop(phone, None)
app.user_sessions.pop(phone, None)
sent.clear()
app.handle_customer_message(phone, "طيب", app.normalize_text("طيب"), {"type": "text"})
assert len(sent) == 1
assert sent[-1][2] == "ابدئي الآن"
assert app.find_response(app.normalize_text("طيب")) is None

sent.clear()
app.user_sessions[phone] = {
    "last_product": {"id": 99001, "name": "صحون كيك تيفال", "price": 3500, "variants": []}
}
app.send_contextual_praise_reply(phone)
assert len(sent) == 1
assert "صحون كيك تيفال" in sent[-1][1]
assert sent[-1][2][0]["id"] == "add_99001"
print("social_conversation_test: OK")
