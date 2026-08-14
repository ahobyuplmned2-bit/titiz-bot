# ربط لوحة Titiz بالبوت

## متغيرات Render المطلوبة

أضف المتغيرين التاليين إلى خدمة `titiz-bot` في Render:

```text
DASHBOARD_API_TOKEN=ضع_توكن_عشوائياً_طويلاً_وخاصاً_بالإدارة
DASHBOARD_ORIGIN=https://titizshop-be9vdk6d.manus.space
```

لا تضع `DASHBOARD_API_TOKEN` داخل React أو داخل GitHub. يحتفظ به Render فقط، وتدخله الإدارة في صفحة `/admin` عند الاتصال.

## واجهات اللوحة

بعد النشر، توفر الخدمة:

```text
GET /admin/api/messages?limit=200
GET /admin/api/summary
GET /admin/api/products
```

يجب إرسال التوكن في الترويسة:

```text
X-Titiz-Admin-Token: قيمة DASHBOARD_API_TOKEN
```

## فتح اللوحة

افتح:

```text
https://titizshop-be9vdk6d.manus.space/admin
```

أدخل رابط خدمة Render وتوكن لوحة الإدارة، ثم اضغط «اتصال». اللوحة تعرض سجل الرسائل، النوايا، الردود، والرسائل التي تحتاج مراجعة.

## حدود الأمان

مفتاح الذكاء الاصطناعي لا ينتقل إلى الموقع. الموقع يتواصل مع API محمي بتوكن الإدارة، والبوت وحده يتواصل مع خدمة الذكاء الاصطناعي. إذا لم تضبط `DASHBOARD_ORIGIN` فلن يسمح المتصفح بطلبات الموقع الخارجية بسبب CORS.
