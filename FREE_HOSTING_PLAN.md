# خطة تشغيل بوت Titiz دون رسوم مستقبلية

## المسار المقترح

المسار الأقل مخاطرة من ناحية الفواتير هو تشغيل نسخة Python/Flask على حساب PythonAnywhere المجاني، مع استخدام cron-job.org المجاني لاستدعاء endpoint التذكيرات كل خمس دقائق. هذا يحافظ على SQLite على مساحة التطبيق بدلاً من تشغيل عامل مدفوع منفصل. يجب تعطيل العامل الداخلي `FOLLOWUP_WORKER_ENABLED=false` حتى لا تعتمد التذكيرات على عملية خلفية قد تتوقف.

حساب PythonAnywhere المجاني يوفر تطبيق Flask واحداً، لكن الوصول الخارجي من الكود محدود بالمواقع المسموح بها، ولا تتوفر المهام المجدولة للحسابات المجانية الجديدة؛ لذلك نستخدم خدمة HTTP خارجية للجدولة. يجب اختبار كل عناوين Meta وGitHub وخدمة الذكاء الاصطناعي المستخدمة قبل التحويل النهائي.

## متطلبات البيئة

يجب ضبط المتغيرات الحالية نفسها الموجودة في Render، مع تغيير `PORT` حسب بيئة WSGI وعدم تخزين أي قيمة سرية داخل GitHub. المتغيرات الأساسية هي `ACCESS_TOKEN` و`PHONE_NUMBER_ID` و`VERIFY_TOKEN` و`APP_SECRET` و`OWNER_NUMBER` و`GITHUB_TOKEN`، إضافة إلى متغيرات الذكاء الاصطناعي والصوت، و`FOLLOWUP_CRON_TOKEN`.

في PythonAnywhere يجب ضبط:

```text
FOLLOWUP_WORKER_ENABLED=false
DATABASE_PATH=/home/<username>/titiz-bot/titiz_bot.db
```

ويجب وضع النسخة الاحتياطية من `titiz_bot.db` في هذا المسار قبل تشغيل التطبيق لأول مرة. لا يجب حذف نسخة Render حتى يتم اختبار الويبهوك الجديد بنجاح.

## التذكيرات

يُنشأ طلب POST في cron-job.org إلى:

```text
https://<username>.pythonanywhere.com/internal/run-followups
```

مع الترويسة التالية:

```text
X-Titiz-Followup-Token: <FOLLOWUP_CRON_TOKEN>
```

والجدولة كل خمس دقائق. يجب أن تكون الاستجابة قصيرة وأن تعيد HTTP 200 عند النجاح. إذا ظهر HTTP 401 فالقيمة السرية غير متطابقة، وإذا ظهر HTTP 5xx يجب فحص سجل التطبيق قبل تكرار الاختبار.

## التحويل النهائي

يُختبر أولاً `/health` ثم تحقق Meta GET للويبهوك. بعد ذلك يُغيّر رابط Callback URL في WhatsApp Cloud API إلى الرابط الجديد ويُستخدم Verify Token نفسه. لا يُغيّر رقم واتساب ولا تُنشر رسائل اجتماعية أثناء عملية النقل. بعد نجاح رسالة اختبار واحدة، تُختبر الصور والبحث والسلة والطلب والتحديثات الإدارية والتذكيرات.

## حدود مهمة

الخطة المجانية ليست ضمان توفر تجاري دائم، وقد تكون لديها حدود CPU أو خروج إلى الإنترنت. كما أن cron-job.org خدمة مجانية بلا ضمان uptime. إذا لم تسمح PythonAnywhere المجانية بالاتصال إلى أحد عناوين Meta أو مزود الذكاء الاصطناعي، يتوقف هذا المسار ويجب عدم نقل الويبهوك إليه قبل حل القيد.

## المصادر

[1]: https://www.pythonanywhere.com/pricing/ "PythonAnywhere plans and pricing"
[2]: https://www.pythonanywhere.com/whitelist/ "PythonAnywhere allowlisted sites"
[3]: https://help.pythonanywhere.com/pages/ScheduledTasks/ "PythonAnywhere scheduled tasks"
[4]: https://cron-job.org/en/ "cron-job.org free scheduled execution"
[5]: https://cron-job.org/en/faq/ "cron-job.org FAQ"
