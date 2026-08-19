# دليل النشر والتشغيل 🚀

## النشر على Render.com

### الخطوة 1: إعداد المستودع

تأكد من أن المستودع يحتوي على:
- `requirements.txt` - قائمة المكتبات
- `Procfile` - تعليمات التشغيل
- `app.py` - الملف الرئيسي

### الخطوة 2: إنشاء خدمة جديدة على Render

1. اذهب إلى [render.com](https://render.com)
2. اختر **New +** ثم **Web Service**
3. اختر مستودع GitHub الخاص بك
4. ملء البيانات:
   - **Name**: `titiz-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### الخطوة 3: إضافة متغيرات البيئة

في قسم **Environment**، أضف:

```
ACCESS_TOKEN=your_whatsapp_token
PHONE_NUMBER_ID=your_phone_id
VERIFY_TOKEN=your_verify_token
OWNER_NUMBER=your_admin_number
GITHUB_TOKEN=your_github_token (اختياري)
PORT=10000
```

### الخطوة 4: النشر

اضغط على **Create Web Service** وانتظر النشر.

---

## النشر على Heroku

### الخطوة 1: تثبيت Heroku CLI

```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

### الخطوة 2: تسجيل الدخول

```bash
heroku login
```

### الخطوة 3: إنشاء تطبيق

```bash
heroku create titiz-bot
```

### الخطوة 4: إضافة متغيرات البيئة

```bash
heroku config:set ACCESS_TOKEN=your_token
heroku config:set PHONE_NUMBER_ID=your_id
heroku config:set VERIFY_TOKEN=your_token
heroku config:set OWNER_NUMBER=your_number
```

### الخطوة 5: النشر

```bash
git push heroku main
```

---

## التشغيل المحلي

### المتطلبات

- Python 3.8+
- pip
- SQLite (مثبت بشكل افتراضي)

### الخطوات

1. **استنساخ المستودع**
```bash
git clone https://github.com/ahobyuplmned2-bit/titiz-bot.git
cd titiz-bot
```

2. **إنشاء بيئة افتراضية**
```bash
python -m venv venv
source venv/bin/activate  # على Windows: venv\Scripts\activate
```

3. **تثبيت المكتبات**
```bash
pip install -r requirements.txt
```

4. **إعداد المتغيرات البيئية**
```bash
cp .env.example .env
# ثم عدّل .env بالقيم الصحيحة
```

5. **تشغيل التطبيق**
```bash
python app.py
```

التطبيق سيعمل على `http://localhost:10000`

---

## إعداد Webhook

### في لوحة تحكم WhatsApp Business

1. اذهب إلى **App Dashboard**
2. اختر **Webhooks**
3. ضع رابط التطبيق: `https://your-domain.com/webhook`
4. ضع **Verify Token** (يجب أن يطابق `VERIFY_TOKEN`)
5. اختر الأحداث المطلوبة:
   - `messages`
   - `message_status`

---

## قاعدة البيانات

### SQLite مع تخزين دائم على Render

يحفظ البوت المنتجات في GitHub، بينما يحفظ محادثات العملاء والسلة والطلبات والتذكيرات في قاعدة SQLite. لكي تبقى هذه البيانات بعد إعادة تشغيل Render أو النشر، أضف قرصاً دائماً من صفحة الخدمة في Render ثم اضبط متغير البيئة التالي:

```text
DATABASE_PATH=/var/data/titiz_bot.db
```

استخدم مسار تركيب القرص `/var/data`. ينشئ البوت المجلد والقاعدة تلقائياً، وينسخ قاعدة البيانات المحلية إليه في أول تشغيل إن كانت متاحة، دون حذف السجل المحلي.

للتذكير بعد 24 ساعة يمكن ترك الإعداد الافتراضي، أو ضبطه صراحةً كالتالي:

```text
PRODUCT_FOLLOWUP_DELAY_SECONDS=86400
```

### PostgreSQL (للإنتاج)

لاستخدام PostgreSQL:

1. أنشئ قاعدة بيانات على Render أو Heroku
2. حدّث `DATABASE_URL` في المتغيرات البيئية
3. عدّل `database.py` لاستخدام PostgreSQL

```python
# في database.py
import psycopg2
# استخدم psycopg2 بدلاً من sqlite3
```

---

## المراقبة والسجلات

### عرض السجلات على Render

```bash
# في لوحة تحكم Render
Logs → View Logs
```

### عرض السجلات على Heroku

```bash
heroku logs --tail
```

### عرض السجلات محلياً

```bash
# السجلات تُطبع على الـ Console
python app.py
```

---

## الصيانة والتحديثات

### تحديث المكتبات

```bash
pip install --upgrade -r requirements.txt
```

### نسخة احتياطية من قاعدة البيانات

```bash
# SQLite
cp titiz_bot.db titiz_bot.db.backup

# PostgreSQL
pg_dump DATABASE_URL > backup.sql
```

### استعادة قاعدة البيانات

```bash
# SQLite
cp titiz_bot.db.backup titiz_bot.db

# PostgreSQL
psql DATABASE_URL < backup.sql
```

---

## استكشاف الأخطاء

### المشكلة: الرسائل لا تصل

**الحل:**
1. تحقق من `ACCESS_TOKEN`
2. تحقق من `PHONE_NUMBER_ID`
3. تحقق من اتصال الإنترنت
4. تحقق من السجلات

### المشكلة: Webhook لا يعمل

**الحل:**
1. تحقق من `VERIFY_TOKEN`
2. تحقق من رابط Webhook
3. تحقق من أن الخادم يعمل
4. اختبر باستخدام `curl`

```bash
curl -X GET "http://localhost:10000/webhook?hub.verify_token=your_token&hub.challenge=test"
```

### المشكلة: قاعدة البيانات لا تعمل

**الحل:**
1. تحقق من صلاحيات الملف
2. تحقق من مساحة التخزين
3. أعد تشغيل التطبيق

---

## الأداء والتحسينات

### تحسين الأداء

1. **استخدم PostgreSQL** بدلاً من SQLite للإنتاج
2. **أضف فهرسة** للجداول الكبيرة
3. **استخدم Caching** للبيانات الثابتة
4. **راقب استخدام الذاكرة**

### توسيع النطاق

1. **استخدم Load Balancer** لعدة نسخ
2. **استخدم CDN** للصور
3. **استخدم Queue** للعمليات الثقيلة

---

## الأمان

### نصائح الأمان

1. **لا تضع التوكنات في الكود** - استخدم متغيرات البيئة
2. **استخدم HTTPS** فقط
3. **تحقق من صلاحيات الإدارة** دائماً
4. **سجّل جميع العمليات** الحساسة
5. **حدّث المكتبات** بانتظام

### إخفاء البيانات الحساسة

```python
# في app.py
if HIDE_ADMIN_NUMBER:
    # لا تعرض رقم الإدارة للعملاء
    pass
```

---

## الدعم والمساعدة

للمساعدة:
- تحقق من [README.md](README.md)
- اقرأ [CHANGELOG.md](CHANGELOG.md)
- افتح Issue على GitHub
- تواصل مع الفريق

---

**آخر تحديث:** يوليو 2026
