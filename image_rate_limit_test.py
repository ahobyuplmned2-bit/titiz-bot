import requests
import app


class RateLimitedResponse:
    status_code = 429
    headers = {"Retry-After": "60"}

    def raise_for_status(self):
        raise requests.HTTPError("429 Too Many Requests", response=self)


calls = []
sleep_calls = []
original_sleep = app.time.sleep
app.time.sleep = lambda seconds: sleep_calls.append(seconds)

try:
    try:
        app._request_with_429_retry(
            lambda *args, **kwargs: calls.append(True) or RateLimitedResponse(),
            "اختبار تحليل الصورة",
            retries=1,
            retry_base=0.2,
        )
    except requests.HTTPError:
        pass
finally:
    app.time.sleep = original_sleep

assert len(calls) == 1
assert sleep_calls == []
print("image_rate_limit_test: OK")
