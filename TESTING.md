# دليل الاختبار 🧪

## اختبار الوحدة (Unit Testing)

### اختبار قاعدة البيانات

```python
# test_database.py
from database import *

def test_add_customer():
    """اختبار إضافة عميل"""
    add_customer("967123456789", "أحمد", "صنعاء")
    customer = get_customer("967123456789")
    assert customer is not None
    assert customer['name'] == "أحمد"
    print("✅ اختبار إضافة عميل نجح")

def test_add_product():
    """اختبار إضافة منتج"""
    product_id = add_product("منتج تجريبي", 100, "وصف تجريبي")
    assert product_id is not None
    product = get_product(product_id)
    assert product['name'] == "منتج تجريبي"
    print("✅ اختبار إضافة منتج نجح")

def test_cart_operations():
    """اختبار عمليات السلة"""
    add_customer("967123456789")
    product_id = add_product("منتج للسلة", 50)
    
    CartManager.add_product("967123456789", product_id, 2)
    items = CartManager.get_cart_items("967123456789")
    assert len(items) > 0
    print("✅ اختبار السلة نجح")

# تشغيل الاختبارات
if __name__ == "__main__":
    test_add_customer()
    test_add_product()
    test_cart_operations()
    print("\n✅ جميع الاختبارات نجحت!")
```

### اختبار نظام الدفع

```python
# test_payment.py
from payment_system import PaymentManager

def test_payment_methods():
    """اختبار طرق الدفع"""
    message = PaymentManager.get_payment_methods_message()
    assert "الدفع عند الاستلام" in message
    assert "التحويل المسبق" in message
    print("✅ اختبار طرق الدفع نجح")

def test_cod_payment():
    """اختبار الدفع عند الاستلام"""
    message = PaymentManager.process_cod_payment("ORD-000001")
    assert "تم تأكيد" in message
    print("✅ اختبار الدفع عند الاستلام نجح")

# تشغيل الاختبارات
if __name__ == "__main__":
    test_payment_methods()
    test_cod_payment()
    print("\n✅ جميع اختبارات الدفع نجحت!")
```

---

## اختبار التكامل (Integration Testing)

### اختبار سير العمل الكامل

```python
# test_workflow.py
from database import *
from cart_system import CartManager, OrderManager
from payment_system import PaymentManager

def test_complete_order_workflow():
    """اختبار سير العمل الكامل من البحث إلى الطلب"""
    
    # 1. إضافة عميل
    phone = "967123456789"
    add_customer(phone, "فاطمة", "صنعاء - الروضة")
    print("✅ تم إضافة العميل")
    
    # 2. إضافة منتجات
    p1 = add_product("فرامة ستانلس", 3000, "فرامة ضغطة ذكية")
    p2 = add_product("ثلاجة شاي", 2500, "ثلاجة شاي أنيقة")
    print("✅ تم إضافة المنتجات")
    
    # 3. إضافة إلى السلة
    CartManager.add_product(phone, p1, 1)
    CartManager.add_product(phone, p2, 2)
    print("✅ تم إضافة المنتجات إلى السلة")
    
    # 4. عرض السلة
    cart_summary = CartManager.get_cart_summary(phone)
    assert cart_summary['total_items'] == 3
    assert cart_summary['total_price'] == 8000
    print(f"✅ السلة: {cart_summary['total_items']} منتجات، {cart_summary['total_price']} ريال")
    
    # 5. إنشاء طلب
    order_number, total = OrderManager.create_from_cart(
        phone, "فاطمة", "صنعاء - الروضة", "الدفع عند الاستلام"
    )
    assert order_number is not None
    print(f"✅ تم إنشاء الطلب: {order_number}")
    
    # 6. التحقق من الطلب
    order = OrderManager.get_order_details(order_number)
    assert order['total_price'] == 8000
    assert order['order_status'] == 'جديد'
    print(f"✅ الطلب: {order_number} - {order['order_status']}")
    
    print("\n✅ سير العمل الكامل نجح!")

if __name__ == "__main__":
    test_complete_order_workflow()
```

---

## اختبار API (API Testing)

### اختبار Webhook

```bash
# اختبار التحقق من Webhook
curl -X GET "http://localhost:10000/webhook?hub.verify_token=bot_adawat_manziliya_2026&hub.challenge=test123"

# يجب أن ترجع: test123
```

### اختبار إرسال رسالة

```bash
# محاكاة رسالة من WhatsApp
curl -X POST "http://localhost:10000/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "msg_123",
            "from": "967123456789",
            "type": "text",
            "text": {
              "body": "السلة"
            }
          }]
        }
      }]
    }]
  }'
```

### اختبار الإحصائيات

```bash
curl -X GET "http://localhost:10000/stats"

# يجب أن ترجع JSON بالإحصائيات
```

---

## اختبار الأداء (Performance Testing)

### اختبار مع عدد كبير من المنتجات

```python
# test_performance.py
import time
from database import add_product, get_all_products

def test_large_product_list():
    """اختبار الأداء مع عدد كبير من المنتجات"""
    
    # إضافة 1000 منتج
    start = time.time()
    for i in range(1000):
        add_product(f"منتج {i}", 100 + i, f"وصف المنتج {i}")
    add_time = time.time() - start
    print(f"⏱️ وقت إضافة 1000 منتج: {add_time:.2f} ثانية")
    
    # جلب جميع المنتجات
    start = time.time()
    products = get_all_products()
    fetch_time = time.time() - start
    print(f"⏱️ وقت جلب المنتجات: {fetch_time:.2f} ثانية")
    print(f"📊 عدد المنتجات: {len(products)}")

if __name__ == "__main__":
    test_large_product_list()
```

---

## اختبار الأمان (Security Testing)

### اختبار صلاحيات الإدارة

```python
# test_security.py
from admin_commands import AdminCommands

def test_admin_permissions():
    """اختبار صلاحيات الإدارة"""
    
    # رقم إدارة صحيح
    assert AdminCommands.is_admin("967773595571") == True
    print("✅ رقم الإدارة الصحيح معترف به")
    
    # رقم عادي
    assert AdminCommands.is_admin("967123456789") == False
    print("✅ الأرقام العادية لا تملك صلاحيات")

def test_command_parsing():
    """اختبار تحليل الأوامر"""
    
    command, args = AdminCommands.parse_command("تفاصيل ORD-000001")
    assert command == "تفاصيل"
    assert args == ["ORD-000001"]
    print("✅ تحليل الأوامر يعمل بشكل صحيح")

if __name__ == "__main__":
    test_admin_permissions()
    test_command_parsing()
    print("\n✅ جميع اختبارات الأمان نجحت!")
```

---

## اختبار يدوي (Manual Testing)

### قائمة الاختبار

- [ ] **البحث عن منتج**
  - اكتب اسم منتج
  - تحقق من ظهور تفاصيل المنتج

- [ ] **إضافة إلى السلة**
  - اضغط "اضف"
  - تحقق من الإشعار

- [ ] **عرض السلة**
  - اكتب "السلة"
  - تحقق من عرض جميع المنتجات والسعر الإجمالي

- [ ] **إكمال الطلب**
  - اكتب "اكمل الطلب"
  - أدخل البيانات المطلوبة
  - تحقق من إنشاء الطلب

- [ ] **الدفع عند الاستلام**
  - اختر الدفع عند الاستلام
  - تحقق من تأكيد الطلب

- [ ] **التحويل المسبق**
  - اختر التحويل المسبق
  - أرسل صورة الإيصال
  - تحقق من تغيير الحالة

- [ ] **أوامر الإدارة**
  - اكتب "مساعدة" من رقم الإدارة
  - اختبر الأوامر المختلفة

---

## تقارير الاختبار

### نموذج تقرير الاختبار

```
التاريخ: 31/7/2026
الإصدار: 2.0.0

✅ اختبارات الوحدة: نجح (8/8)
✅ اختبارات التكامل: نجح (5/5)
✅ اختبارات API: نجح (3/3)
✅ اختبارات الأداء: نجح
✅ اختبارات الأمان: نجح (2/2)

ملاحظات:
- جميع الاختبارات نجحت
- لا توجد أخطاء حرجة
- الأداء مقبول

التوصيات:
- إضافة مزيد من اختبارات الحمل
- مراقبة استخدام الذاكرة
```

---

## الأدوات المساعدة

### Postman

استيراد المجموعة:

```json
{
  "info": {
    "name": "Titiz Bot API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Webhook Verification",
      "request": {
        "method": "GET",
        "url": "http://localhost:10000/webhook?hub.verify_token=bot_adawat_manziliya_2026&hub.challenge=test"
      }
    },
    {
      "name": "Get Statistics",
      "request": {
        "method": "GET",
        "url": "http://localhost:10000/stats"
      }
    }
  ]
}
```

### curl Scripts

```bash
#!/bin/bash
# test.sh

echo "🧪 اختبار Titiz Bot API"

echo "1️⃣ اختبار التحقق من Webhook..."
curl -s "http://localhost:10000/webhook?hub.verify_token=bot_adawat_manziliya_2026&hub.challenge=test" | head -c 50
echo ""

echo "2️⃣ اختبار الإحصائيات..."
curl -s "http://localhost:10000/stats" | python -m json.tool | head -20
echo ""

echo "✅ الاختبارات اكتملت"
```

---

## الخطوات التالية

1. **تشغيل الاختبارات المحلية**
2. **اختبار على بيئة التطوير**
3. **اختبار على بيئة الإنتاج**
4. **مراقبة الأداء والأخطاء**

---

**آخر تحديث:** يوليو 2026
