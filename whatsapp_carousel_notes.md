# ملاحظات كاروسيل واتساب

وفق وثائق Meta الرسمية المحدثة في مايو ويونيو 2026، يدعم WhatsApp Cloud API كاروسيل وسائط تفاعلياً من بطاقتين إلى عشر بطاقات، مع صورة أو فيديو في رأس كل بطاقة، ونص جسم، وأزرار سريعة أو زر رابط. يجب أن تتطابق أنواع وعدد الأزرار بين البطاقات، وأن تكون الصور روابط عامة مباشرة.

يدعم كاروسيل المنتجات المعتمد على كتالوج WhatsApp بطاقات منتجات أفقية أيضاً، لكنه يحتاج `catalog_id` و`product_retailer_id` لكل بطاقة، لذلك لا يناسب المنتجات المخزنة حالياً في `products.json` بدون ربط كتالوج Meta.

المراجع:

- https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/interactive-media-carousel-messages/
- https://developers.facebook.com/documentation/business-messaging/whatsapp/catalogs/interactive-product-carousel-messages/
- https://docs.360dialog.com/docs/messaging/message-types/interactive/media-carousel

ملاحظة الإصلاح: عند رفض Meta للكاروسيل يجب تسجيل نص الاستجابة الكامل، ثم إرسال صورة واحدة وبطاقة أزرار كبديل حتى لا يختفي المنتج عن العميل.

توضيح مهم من المثال الرسمي لبطاقات quick-reply: قيمة `cards[].type` يجب أن تكون `cta_url` حتى عند استخدام `action.buttons` للـ quick replies؛ أما `action.name` و`parameters` فيُستخدمان مع زر الرابط. هذا يفسر احتمال خطأ 400 في النسخة السابقة التي استخدمت `type: quick_reply`.
