# ملاحظات Render Cron المستخدمة في إصلاح التذكيرات

تمت مراجعة وثائق Render الرسمية في 23-08-2026:

1. [Blueprint YAML Reference](https://render.com/docs/blueprint-spec): يعرّف خدمة `type: cron` باستخدام `runtime`, `schedule`, `buildCommand`, و`startCommand`، ويمكن مشاركة متغيرات البيئة عبر `envVarGroups`.
2. [Cron Jobs](https://render.com/docs/cronjobs): مهمة Render Cron تعمل وفق تعبير cron بتوقيت UTC، تنفذ أمراً يجب أن ينتهي عند اكتماله، ولا تستطيع الوصول إلى قرص دائم. لذلك يستدعي cron endpoint خدمة الويب، بينما تبقى قاعدة البيانات ذات القرص الدائم داخل خدمة الويب.

القرار التطبيقي: إضافة cron كل 5 دقائق يستدعي `/internal/run-followups` بتوكن مشترك، مع إبقاء العامل داخل الويب كحل احتياطي فقط. التذكيرات الفاشلة لا تُعلّم مرسلة، وتُعاد محاولتها في الدورة التالية.
