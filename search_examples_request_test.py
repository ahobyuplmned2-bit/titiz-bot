import app


sent = []
app.send_message = lambda to, text: sent.append((to, text))

assert app.is_search_examples_request(app.normalize_text("مثل ايش اكتب"))
assert app.is_search_examples_request(app.normalize_text("مثلاً ايش أكتب؟"))
assert app.is_search_examples_request(app.normalize_text("وش اكتب لكم"))
assert not app.is_search_examples_request(app.normalize_text("صحون فرم حراري"))

app.send_search_examples("967700000000")
assert len(sent) == 1
assert "كتلي شاي" in sent[0][1]
assert "سلال رحلات" in sent[0][1]

print("search_examples_request_test: OK")
