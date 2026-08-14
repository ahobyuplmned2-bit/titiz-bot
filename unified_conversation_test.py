import app


sent = []
app.restore_customer_session = lambda recipient: None
app.cancel_customer_followup = lambda recipient: None
app.send_message = lambda recipient, text: sent.append(("message", recipient, text))
app.send_buttons = lambda recipient, text, buttons: sent.append(("buttons", recipient, text, buttons))
app.send_list = lambda recipient, body, button_text, sections: sent.append(
    ("list", recipient, body, button_text, sections)
)
app.get_all_products = lambda: []
app.find_response = lambda normalized: None


def fake_interpret(sender, text):
    if text == "ارسل لي منتج":
        return {"intent": "product_search", "confidence": 0.96, "search_query": "", "reply": ""}
    if text == "هيا ارسو الخبر":
        return {
            "intent": "social_chat",
            "confidence": 0.91,
            "search_query": "",
            "reply": "أكيد يا غالية 😊 قولي لي ما الذي تحتاجينه من Titiz؟",
        }
    return None


app.interpret_customer_message = fake_interpret

for phone, text in [
    ("967700001001", "ارسل لي منتج"),
    ("967700001002", "هيا ارسو الخبر"),
    ("967700001003", "ما تفهم"),
]:
    app.user_states.pop(phone, None)
    app.user_sessions.pop(phone, None)
    sent.clear()
    app.handle_customer_message(phone, text, app.normalize_text(text), {"type": "text"})
    assert len(sent) == 1, (text, sent)

assert sent[0][0] == "list"
assert "حقك علي" in sent[0][2]

sent.clear()
app.handle_customer_message("967700001004", "menu_products", "menuproducts", {"type": "text"})
assert len(sent) == 1
assert sent[0][0] == "buttons"
assert "اكتبي اسم الأداة" in sent[0][2]

print("unified_conversation_test: OK")
