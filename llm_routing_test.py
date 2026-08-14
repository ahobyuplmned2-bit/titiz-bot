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


app.SMART_AI_API_KEY = "test-key"
app.get_all_products = lambda: [{"name": "طقم قدور هندي", "keywords": "قدور, هندي", "description": "طقم قدور"}]
app.build_conversation_context = lambda sender: "العميل: أريد قدور"
app.requests.post = lambda *args, **kwargs: FakeResponse()
result = app.interpret_customer_message("967700000000", "قذور هندي")
assert result["intent"] == "product_search"
assert result["search_query"] == "قدور هندي"

print("llm_routing_test: OK")
