import app


product = {
    "id": 910,
    "name": "كتلي شاي تجريبي",
    "price": "2700",
    "quantity": 10,
    "variants": [
        {"name": "1 لتر", "price": "2700"},
        {"name": "2 لتر", "price": "4000"},
    ],
}

cart_items = []
messages = []
buttons = []

app.get_product = lambda product_id: product if int(product_id) == 910 else None
app.add_to_cart = lambda recipient, product_id, quantity, variant_name=None, variant_price=None: cart_items.append(
    (recipient, product_id, quantity, variant_name, variant_price)
) or True
app.send_message = lambda recipient, text: messages.append((recipient, text)) or True
app.send_buttons = lambda recipient, text, options: buttons.append((recipient, text, options)) or True
app.cancel_customer_followup = lambda recipient: None

app.handle_customer_message("967700000000", "variant_910_1", "variant_910_1", {"type": "interactive"})

assert cart_items == [("967700000000", 910, 1, "2 لتر", 4000.0)]
assert len(messages) == 1 and "2 لتر" in messages[0][1] and "4000" in messages[0][1]
assert len(buttons) == 1 and buttons[0][2][0]["id"] == "menu_cart"

print("variant_add_to_cart_test: OK")
