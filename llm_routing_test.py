import app


class FakeResponse:
    status_code = 200
    headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{
                "message": {
                    "content": '{"intent":"product_search","confidence":0.94,"search_query":"قدور هندي","reply":""}'
                }
            }]
        }


captured_payloads = []


def fake_post(*args, **kwargs):
    captured_payloads.append(kwargs.get("json") or {})
    return FakeResponse()


app.SMART_AI_API_KEY = "test-key"
app.SMART_AI_MODEL = "gpt-5-mini"
app.get_all_products = lambda: [{"name": "طقم قدور هندي", "keywords": "قدور, هندي", "description": "طقم قدور"}]
app.build_conversation_context = lambda sender: "العميل: أريد قدور"
app.requests.post = fake_post
result = app.interpret_customer_message("967700000000", "قذور هندي")
assert result["intent"] == "product_search"
assert result["search_query"] == "قدور هندي"
assert captured_payloads[-1]["max_completion_tokens"] == 300
assert "max_tokens" not in captured_payloads[-1]
schema = captured_payloads[-1]["response_format"]["json_schema"]["schema"]
assert schema["additionalProperties"] is False
assert "shipping" in schema["properties"]["intent"]["enum"]
assert "out_of_scope" in schema["properties"]["intent"]["enum"]
assert app._llm_token_limit(123) == {"max_completion_tokens": 123}
app.SMART_AI_MODEL = "gemini-3-flash-preview"
assert app._llm_token_limit(123) == {"max_tokens": 123}

print("llm_routing_test: OK")
