import app


sent = []
app.send_message = lambda recipient, text: sent.append((recipient, text))
app.send_welcome = lambda recipient: sent.append((recipient, "welcome"))
app.send_product_card = lambda recipient, product: sent.append((recipient, product.get("name")))
app.send_cart_view = lambda recipient: sent.append((recipient, "cart"))
app.cancel_customer_followup = lambda recipient: sent.append((recipient, "followup_cancelled"))
app.whatsapp.send_url_button = lambda recipient, text, title, url: sent.append((recipient, title, url)) or True

assert app.route_semantic_intent(
    "967700000000",
    "ههههه",
    {"intent": "social_chat", "reply": "ههههه منورة 😊 كيف أساعدك؟"},
    [],
)
assert "منورة" in sent[-1][1]

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
print("social_conversation_test: OK")
