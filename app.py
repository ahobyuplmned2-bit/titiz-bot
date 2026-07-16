from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

ACCESS_TOKEN = "EAAVV1mNUcEkBRZCKz7cZAPn3Dc0NE33WUQm7kjSQ6bLJzT7iA0IswVwteUoSHInm2aW690MiEPT87UjciE9c5Bk0VQl9cMZBloQZCF3u4bZAEFrXCqrikv68EnaOPaZAZBAQXEhfCpWWNXGP68E5DPqxUa4hP5ZBeiVTqsnQZADrEHAR8zqESGtZAtn2EXWxZBI3QZDZD"
PHONE_NUMBER_ID = "1097018736835171"
VERIFY_TOKEN = "bot_adawat_manziliya_2026"
OWNER_NUMBER = "967773595571"  # رقم المالك لاستقبال الإشعارات

# Image URLs for products
IMG_QUDOR = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/FErlTSZcVDmLLuCl.jpg"
IMG_THALAJA = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663669337302/yCftQDzESzArGegt.jpg"
# Media IDs for فرامة images
IMG_FARAMA_BIG = "1722172418808924"  # كبير MD-5266
IMG_FARAMA_MED = "1788826688946693"  # وسط MD-5076
IMG_FARAMA_SML = "1340222830997132"  # صغير MD-5066

# قائمة الزبائن اللي راسلوا البوت
customers = []

# === نظام إدارة المنتجات ===
PRODUCTS_FILE = "products.json"

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_products(products):
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# تحميل المنتجات عند بدء التشغيل
custom_products = load_products()

# Product responses
RESP_FARAMA = "🔴 *فرامة الضغطة الذكية من المائدة* 🔪\n\nالمميزات:\n✅ توفّر عليكِ 60% من وقت التقطيع\n✅ شفرات فولاذ ضد الصدأ\n✅ سهلة التنظيف والاستخدام\n✅ تقطع كمية كبيرة مرة وحدة\n\n💰 *الأسعار:*\n🔴 الكبير (MD-5266): 3,000 ريال\n🟢 الوسط (MD-5076): 2,500 ريال\n🟢 الصغير (MD-5066): 2,000 ريال\n\n🚚 التوصيل مجاني داخل المحافظة!\n⚠️ احذروا التقليد - اطلبيها باسمها من المائدة\n\nاكتبي *اطلب* للطلب 😍"

RESP_QUDOR = "🍲 *طقم قدور المائدة 4 قطع - هندي*\n\n✅ ستانلس ثقيل + أغطية استيل\n✅ 4 مقاسات: كبير/وسط/صغير/صغير جداً\n✅ ضمان المائدة\n\n💰 *الأسعار:*\nالكبير 3,500 | الوسط 3,000\nالصغير 2,500 | الصغير جداً 2,000\n\n🎁 *الطقم كامل:* 10,500 ريال - وفر 1,000\n🚚 توصيل مجاني لداخل المحافظة\n\nاكتب *اطلب* للطلب"
RESP_THALAJA = "☕ *ثلاجة شاي المائدة M213 - 0.7 لتر*\n\n✅ تحفظ الحرارة 6 ساعات\n✅ الألوان: وردي 💗 | بيج 🤎 | أزرق 💙 | كحلي\n✅ تصميم أنيق للضيافة\n\n💰 السعر: 2,500 ريال\n\n🚚 توصيل مجاني لداخل المحافظة\n⏰ الكمية محدودة\n\nاكتب *اطلب* للطلب"
RESP_ORDER = "🛒 *لإتمام الطلب:*\n\nأرسل لنا:\n1. اسم المنتج اللي تبيه\n2. اسمك الكامل\n3. عنوان التوصيل\n4. رقم تواصل آخر (اختياري)\n\n💳 الدفع عند الاستلام\n📦 التوصيل مجاني داخل المحافظة!\n\nوسيتم التواصل معك لتأكيد الطلب ✅"
# ردود التحية - بسيطة بدون ذكر منتجات
RESP_SALAM = "وعليكم السلام ورحمة الله 🤲✨\nنورتينا يا غالية! بايش نخدمكِ؟ 😊"
RESP_HALA = "هلا وغلا فيكِ! 💛✨\nنورتي والله! بايش نخدمكِ؟ 😊"
RESP_MARHABA = "مرحباً فيكِ! 🌸✨\nأهلاً وسهلاً! بايش نقدر نساعدكِ؟ 😊"
RESP_SABAH = "صباح النور والسعادة! ☀️🌺\nيسعد صباحكِ! بايش نخدمكِ؟ 😊"
RESP_MASA = "مساء النور والورد! 🌙✨\nأهلاً فيكِ! بايش نخدمكِ؟ 😊"
RESP_KAIF = "الحمد لله بخير! الله يسعدكِ 😊💛\nبايش نقدر نخدمكِ؟"
RESP_AFYA = "الله يعافيكِ يا قلبي! 🙏💛\nنورتينا! بايش نخدمكِ؟ 😊"
RESP_AHLAN = "أهلين فيكِ! 💛✨\nحياكِ الله! بايش نخدمكِ؟ 😊"
RESP_HAI = "هايي! 👋😊\nأهلاً فيكِ! بايش نقدر نساعدكِ؟ 💛"
RESP_SHUKR = "العفو يا غالية! 🙏✨\nإحنا في خدمتكِ دائماً! 😊"

# رد الزبون الجديد - رسائل منفصلة
RESP_NEW_CUSTOMER = [
    "يا أهلاً وسهلاً فيكِ! 🤩💛\nشرفتينا والله! نحن سعيدين بكِ معنا ❤️\nفي *Titiz* نهتم بكل زبونة ونعاملها زي العائلة 🏠",
    "✨ *ليش تختارينا:*\n\n✅ منتجات أصلية وجودة عالية\n✅ أسعار مناسبة للجميع\n✅ توصيل مجاني لباب بيتكِ 🚚\n✅ الدفع عند الاستلام - بدون مخاطرة\n✅ استبدال خلال 7 أيام",
    "اكتبي *قدور* أو *ثلاجة* وشوفي بنفسكِ 😍\nأو اكتبي *1* لكل المنتجات\n\n💡 *زبائننا دائماً يرجعوا لنا!* 👌"
]

# رد التوصيل
RESP_DELIVERY = "🚚 *التوصيل والشحن:*\n\n✅ داخل محافظة إب: *مجاني* تماماً!\n📦 باقي المحافظات: 2-4 أيام\n💳 الدفع عند الاستلام\n\nيعني ما فيه أي مخاطرة عليكِ 😊"

# رد الدفع
RESP_PAYMENT = "💳 *طرق الدفع:*\n\n✅ *الدفع عند الاستلام:*\nنحط المنتج لأقرب نقطة منكِ وتدفعي وقت الاستلام 👌\n\n✅ *التحويل المسبق:*\nتدفعي وإحنا نوصل لكِ الطلب لباب بيتكِ 🚚\n\n💰 *حسابات التحويل:*\n\n🟢 *نقطة جيب:* 906072\n🟡 *الكريمي نقطة حاسب:* 1202686\n🏦 *إيداع عبر الكريمي:* 3122678098\n\nاختاري الطريقة اللي تناسبكِ 😊"

# رد الضمان والاستبدال
RESP_GUARANTEE = "🔄 *الضمان والاستبدال:*\n\n✅ استبدال خلال 7 أيام من الاستلام\n✅ استرجاع خلال 3 أيام (بحالته الأصلية)\n✅ ضمان المائدة على المنتجات\n\nإحنا واثقين من جودة منتجاتنا 👌"

# رد الألوان
RESP_COLORS = "🎨 *الألوان المتوفرة:*\n\n☕ ثلاجة الشاي:\n💗 وردي | 🤎 بيج | 💙 أزرق | كحلي\n\nاكتبي *ثلاجة* لتشوفي الصورة 😍"

# رد المقاسات
RESP_SIZES = "📏 *المقاسات المتوفرة:*\n\n🍲 طقم القدور - 4 مقاسات:\n• كبير - 3,500 ريال\n• وسط - 3,000 ريال\n• صغير - 2,500 ريال\n• صغير جداً - 2,000 ريال\n\n🎁 الطقم كامل: 10,500 ريال (وفري 1,000!) 🔥"

# رد الجودة
RESP_QUALITY = "⭐ *جودة منتجاتنا:*\n\n✅ ستانلس ستيل ثقيل - ما يصدي\n✅ ماركة المائدة الأصلية\n✅ ضمان على كل منتج\n✅ زبائننا شهاداتهم أفضل دليل 👌\n\nجربي وما راح تندمي! 😊"

# رد العروض
RESP_OFFERS = "🔥 *عروضنا الحالية:*\n\n🎁 طقم القدور كامل 4 قطع: 10,500 بدل 11,500 - وفري 1,000 ريال!\n🚚 توصيل مجاني لكل الطلبات\n\n⭐ العرض لفترة محدودة! لا تفوتكِ 😍"

# رد الثقة والمصداقية
RESP_TRUST = "🤝 *ليش تثقين فينا:*\n\n✅ عندنا محلين في إب تقدري تزورينا 🏪\n✅ الدفع عند الاستلام - ما نطلب فلوس مقدماً\n✅ استبدال خلال 7 أيام لو ما عجبكِ\n✅ زبائننا كثير والحمد لله راضين\n✅ نشتغل بسمعتنا وما نغش أي زبون\n\n📍 *عناويننا:*\n🏪 إب - بوابة ملعب الكبسي الخلفية\n🏪 السوق المركزي القديم\n\nجربي واحكمي بنفسكِ 😊👌"

# رد السؤال عن المنتجات - بسيط يسأل الزبون ايش يبي
RESP_PRODUCTS_ASK = "🏠 أهلاً فيكِ يا غالية! ✨\n\nلدينا جميع الأدوات المنزلية ومستلزمات المطابخ 🍳\n\nايش بدكِ أنتِ من منتج؟ 😊\n\nمثلاً:\n🍲 اكتبي *قدور* - طقم قدور ستانلس\n☕ اكتبي *ثلاجة* - ثلاجة شاي أنيقة\n🔪 اكتبي *1* - لكل المنتجات والأسعار"

# رد مكان استلام المنتج
RESP_WHERE_DELIVER = "📦 وين تحبين نحط لكِ المنتج؟ 🤔\n\nنقدر نحطه في أي مكان قريب منكِ:\n\n🏪 محل قريب من بيتكِ\n🛍️ بقالة في حارتكِ\n📍 أي نقطة تحدديها\n\nأرسلي لنا اسم المكان أو المنطقة وإحنا نوصله لأقرب نقطة منكِ 😊👌"

# رد الوداع
RESP_BYE = "مع السلامة يا غالية! 💛👋\nنورتينا والله!\nإحنا هنا بأي وقت تحتاجينا 😊\nلا تنسينا! ❤️"

# رد الموقع
RESP_LOCATION = "📍 *مواقع محلات Titiz:*\n\n🏪 *الفرع الأول:*\nإب - بوابة ملعب الكبسي الخلفية\nنهاية طلعة صرافة الكريمي\n\n🏪 *الفرع الثاني:*\nالسوق المركزي القديم\nأمام صرافة فيصل الخطيب\n\n📞 للتواصل: +967 773 595 571\n✅ نستقبلكِ بأي وقت!"

RESPONSES = {
    "1": "🏠 *المنتجات والأسعار:*\n\nنوفر تشكيلة واسعة من الأدوات المنزلية:\n\n🔴 *فرامة الضغطة الذكية (المائدة MD-5266):*\n- شفرات فولاذية ضد الصدأ\n- قوة إضافية لتوفير الوقت 60%\n- سهلة الاستخدام\n- السعر: 2,800 ريال\n\n🍲 *طقم قدور المائدة 4 قطع - هندي:*\n- ستانلس ثقيل + أغطية استيل\n- 4 مقاسات: كبير/وسط/صغير/صغير جداً\n- ضمان المائدة\n- الكبير 3,500 | الوسط 3,000 | الصغير 2,500 | الصغير جداً 2,000\n- 🎁 الطقم كامل: 10,500 ريال (وفر 1,000)\n\n☕ *ثلاجة شاي المائدة M213 - 0.7 لتر:*\n- تحفظ الحرارة 6 ساعات\n- الألوان: وردي | بيج | أزرق | كحلي\n- تصميم أنيق للضيافة\n- السعر: 2,500 ريال\n\n📦 التوصيل مجاني داخل المحافظة!\nللمزيد من المنتجات تواصل معنا.\n\nأرسل *قدور* لتفاصيل طقم القدور\nأرسل *ثلاجة* لتفاصيل ثلاجة الشاي",
    "2": "🛒 *طريقة الطلب:*\nيمكنك الطلب عبر:\n1. إرسال اسم المنتج أو صورته هنا.\n2. تزويدنا بالاسم والعنوان.\n3. اختيار وسيلة الدفع (عند الاستلام أو تحويل).\n\n📦 التوصيل مجاني داخل المحافظة!",
    "3": "🚚 *التوصيل والشحن:*\n- التوصيل داخل محافظة إب: *مجاني* ✅\n- الشحن لباقي المحافظات: 2-4 أيام.",
    "4": "🔄 *سياسة الاستبدال والاسترجاع:*\n- الاستبدال خلال 7 أيام من تاريخ الاستلام.\n- الاسترجاع خلال 3 أيام بشرط أن يكون المنتج بحالته الأصلية.",
    "5": "⏰ *مواعيد العمل:*\nمن السبت إلى الخميس:\n- الفترة الصباحية: 9:00 ص - 12:00 م\n- الفترة المسائية: 4:00 م - 10:00 م\nالجمعة: من 4:00 م - 10:00 م",
    "6": RESP_LOCATION,
    # === المنتجات - الفرامة ===
    "فرامة": RESP_FARAMA,
    "فرامه": RESP_FARAMA,
    "الفرامة": RESP_FARAMA,
    "الفرامه": RESP_FARAMA,
    "فرامة الضغطة": RESP_FARAMA,
    "فرامه الضغطه": RESP_FARAMA,
    "فرامة الضغطه": RESP_FARAMA,
    "فرامه الضغطة": RESP_FARAMA,
    "الفرامة الذكية": RESP_FARAMA,
    "الفرامه الذكيه": RESP_FARAMA,
    "فرامة ذكية": RESP_FARAMA,
    "فرامه ذكيه": RESP_FARAMA,
    "عصارة": RESP_FARAMA,
    "عصاره": RESP_FARAMA,
    "العصارة": RESP_FARAMA,
    "العصاره": RESP_FARAMA,
    "فرامة المائدة": RESP_FARAMA,
    "فرامه المائده": RESP_FARAMA,
    "فرامة المائده": RESP_FARAMA,
    "فرامه المائدة": RESP_FARAMA,
    "فرامة خضار": RESP_FARAMA,
    "فرامه خضار": RESP_FARAMA,
    "قطاعة": RESP_FARAMA,
    "قطاعه": RESP_FARAMA,
    "القطاعة": RESP_FARAMA,
    "القطاعه": RESP_FARAMA,
    "مفرمة": RESP_FARAMA,
    "مفرمه": RESP_FARAMA,
    "المفرمة": RESP_FARAMA,
    "المفرمه": RESP_FARAMA,
    "خلاط": RESP_FARAMA,
    "الخلاط": RESP_FARAMA,
    "فرامة ضغطة": RESP_FARAMA,
    "فرامه ضغطه": RESP_FARAMA,
    "ضغطة ذكية": RESP_FARAMA,
    "ضغطه ذكيه": RESP_FARAMA,
    # === المنتجات - القدور ===
    "قدور": RESP_QUDOR,
    "القدور": RESP_QUDOR,
    "قدر": RESP_QUDOR,
    "القدر": RESP_QUDOR,
    "طقم قدور": RESP_QUDOR,
    "طقم القدور": RESP_QUDOR,
    "قدور المائدة": RESP_QUDOR,
    "قدور المائده": RESP_QUDOR,
    "قدور هندي": RESP_QUDOR,
    "قدور ستانلس": RESP_QUDOR,
    "طقم": RESP_QUDOR,
    # === المنتجات - الثلاجة ===
    "ثلاجة": RESP_THALAJA,
    "ثلاجه": RESP_THALAJA,
    "الثلاجة": RESP_THALAJA,
    "الثلاجه": RESP_THALAJA,
    "شاي": RESP_THALAJA,
    "ثلاجة شاي": RESP_THALAJA,
    "ثلاجه شاي": RESP_THALAJA,
    "ثلاجة الشاي": RESP_THALAJA,
    "ثلاجه الشاي": RESP_THALAJA,
    "ترمس": RESP_THALAJA,
    "ترمز": RESP_THALAJA,
    "حافظة": RESP_THALAJA,
    "حافظه": RESP_THALAJA,
    # === زبون جديد ===
    "زبون": RESP_NEW_CUSTOMER,
    "زبونه": RESP_NEW_CUSTOMER,
    "زبونة": RESP_NEW_CUSTOMER,
    "عميل": RESP_NEW_CUSTOMER,
    "عميله": RESP_NEW_CUSTOMER,
    "عميلة": RESP_NEW_CUSTOMER,
    "ابي اكون زبونه": RESP_NEW_CUSTOMER,
    "ابي اكون زبونة": RESP_NEW_CUSTOMER,
    "اشتي اكون زبونه": RESP_NEW_CUSTOMER,
    "اشتي اكون زبونة": RESP_NEW_CUSTOMER,
    "اريد اكون زبونه": RESP_NEW_CUSTOMER,
    "اريد اكون زبونة": RESP_NEW_CUSTOMER,
    "بدي اكون زبونه": RESP_NEW_CUSTOMER,
    "بدي اكون زبونة": RESP_NEW_CUSTOMER,
    "زبون جديد": RESP_NEW_CUSTOMER,
    "زبونه جديده": RESP_NEW_CUSTOMER,
    "زبونة جديدة": RESP_NEW_CUSTOMER,
    "عميل جديد": RESP_NEW_CUSTOMER,
    "عميله جديده": RESP_NEW_CUSTOMER,
    "عميلة جديدة": RESP_NEW_CUSTOMER,
    "ابي اتعامل معاكم": RESP_NEW_CUSTOMER,
    "اشتي اتعامل معاكم": RESP_NEW_CUSTOMER,
    "اريد اتعامل معاكم": RESP_NEW_CUSTOMER,
    # === التوصيل ===
    "توصيل": RESP_DELIVERY,
    "التوصيل": RESP_DELIVERY,
    "شحن": RESP_DELIVERY,
    "الشحن": RESP_DELIVERY,
    "توصلون": RESP_DELIVERY,
    "توصلوا": RESP_DELIVERY,
    "كيف التوصيل": RESP_DELIVERY,
    "كم التوصيل": RESP_DELIVERY,
    "التوصيل مجاني": RESP_DELIVERY,
    "هل فيه توصيل": RESP_DELIVERY,
    "فيه توصيل": RESP_DELIVERY,
    "عندكم توصيل": RESP_DELIVERY,
    "توصيل مجاني": RESP_DELIVERY,
    # === الدفع ===
    "دفع": RESP_PAYMENT,
    "الدفع": RESP_PAYMENT,
    "كيف ادفع": RESP_PAYMENT,
    "كيف الدفع": RESP_PAYMENT,
    "طريقة الدفع": RESP_PAYMENT,
    "طريقه الدفع": RESP_PAYMENT,
    "كاش": RESP_PAYMENT,
    "تحويل": RESP_PAYMENT,
    "عند الاستلام": RESP_PAYMENT,
    # === الضمان والاستبدال ===
    "ضمان": RESP_GUARANTEE,
    "الضمان": RESP_GUARANTEE,
    "استبدال": RESP_GUARANTEE,
    "الاستبدال": RESP_GUARANTEE,
    "استرجاع": RESP_GUARANTEE,
    "الاسترجاع": RESP_GUARANTEE,
    "ارجاع": RESP_GUARANTEE,
    "ارجعه": RESP_GUARANTEE,
    "ارجعة": RESP_GUARANTEE,
    "لو ما عجبني": RESP_GUARANTEE,
    "اذا ما عجبني": RESP_GUARANTEE,
    "لو فيه مشكلة": RESP_GUARANTEE,
    "لو فيه مشكله": RESP_GUARANTEE,
    # === الألوان ===
    "الوان": RESP_COLORS,
    "ألوان": RESP_COLORS,
    "الالوان": RESP_COLORS,
    "الألوان": RESP_COLORS,
    "ايش الالوان": RESP_COLORS,
    "شو الالوان": RESP_COLORS,
    "لون": RESP_COLORS,
    # === المقاسات ===
    "مقاس": RESP_SIZES,
    "مقاسات": RESP_SIZES,
    "المقاسات": RESP_SIZES,
    "حجم": RESP_SIZES,
    "احجام": RESP_SIZES,
    "الاحجام": RESP_SIZES,
    "كبير": RESP_SIZES,
    "صغير": RESP_SIZES,
    "وسط": RESP_SIZES,
    # === الجودة ===
    "جودة": RESP_QUALITY,
    "جوده": RESP_QUALITY,
    "الجودة": RESP_QUALITY,
    "الجوده": RESP_QUALITY,
    "اصلي": RESP_QUALITY,
    "أصلي": RESP_QUALITY,
    "اصليه": RESP_QUALITY,
    "أصلية": RESP_QUALITY,
    "هل اصلي": RESP_QUALITY,
    "النوعية": RESP_QUALITY,
    "نوعية": RESP_QUALITY,
    "نوعيه": RESP_QUALITY,
    # === العروض ===
    "عروض": RESP_OFFERS,
    "العروض": RESP_OFFERS,
    "عرض": RESP_OFFERS,
    "خصم": RESP_OFFERS,
    "خصومات": RESP_OFFERS,
    "تخفيض": RESP_OFFERS,
    "تخفيضات": RESP_OFFERS,
    "فيه عرض": RESP_OFFERS,
    "فيه خصم": RESP_OFFERS,
    "عندكم عروض": RESP_OFFERS,
    # === الثقة والمصداقية ===
    "ثقة": RESP_TRUST,
    "ثقه": RESP_TRUST,
    "الثقة": RESP_TRUST,
    "الثقه": RESP_TRUST,
    "كيف نوثق بكم": RESP_TRUST,
    "كيف اثق فيكم": RESP_TRUST,
    "كيف اثق بكم": RESP_TRUST,
    "نوثق": RESP_TRUST,
    "نثق": RESP_TRUST,
    "مصداقية": RESP_TRUST,
    "مصداقيه": RESP_TRUST,
    "موثوق": RESP_TRUST,
    "موثوقين": RESP_TRUST,
    "نصب": RESP_TRUST,
    "نصاب": RESP_TRUST,
    "نصابين": RESP_TRUST,
    "كذب": RESP_TRUST,
    "تكذبون": RESP_TRUST,
    "تكذبوا": RESP_TRUST,
    "كذابين": RESP_TRUST,
    "غش": RESP_TRUST,
    "تغشون": RESP_TRUST,
    "تغشوا": RESP_TRUST,
    "غشاشين": RESP_TRUST,
    "مضمون": RESP_TRUST,
    "مضمونين": RESP_TRUST,
    "هل انتم موثوقين": RESP_TRUST,
    "انتو صادقين": RESP_TRUST,
    "انتم صادقين": RESP_TRUST,
    "كيف اعرف انكم": RESP_TRUST,
    "كيف نعرف انكم": RESP_TRUST,
    "ما نعرفكم": RESP_TRUST,
    "ما اعرفكم": RESP_TRUST,
    "خايفه": RESP_TRUST,
    "خايفة": RESP_TRUST,
    "خايف": RESP_TRUST,
    "متردده": RESP_TRUST,
    "مترددة": RESP_TRUST,
    "متردد": RESP_TRUST,
    "اخاف": RESP_TRUST,
    "أخاف": RESP_TRUST,
    "محتاره": RESP_TRUST,
    "محتارة": RESP_TRUST,
    "احتيال": RESP_TRUST,
    # === الوداع ===
    "مع السلامة": RESP_BYE,
    "مع السلامه": RESP_BYE,
    "باي": RESP_BYE,
    "بااي": RESP_BYE,
    "bye": RESP_BYE,
    "الله معك": RESP_BYE,
    "الله معكم": RESP_BYE,
    "في امان الله": RESP_BYE,
    "في أمان الله": RESP_BYE,
    "الله يحفظك": RESP_BYE,
    "الله يحفظكم": RESP_BYE,
    # === السؤال عن المنتجات ===
    "منتجات": RESP_PRODUCTS_ASK,
    "المنتجات": RESP_PRODUCTS_ASK,
    "منتجاتكم": RESP_PRODUCTS_ASK,
    "بضاعة": RESP_PRODUCTS_ASK,
    "بضاعه": RESP_PRODUCTS_ASK,
    "البضاعة": RESP_PRODUCTS_ASK,
    "البضاعه": RESP_PRODUCTS_ASK,
    "بضاعتكم": RESP_PRODUCTS_ASK,
    "ايش عندكم": RESP_PRODUCTS_ASK,
    "ايش معاكم": RESP_PRODUCTS_ASK,
    "وش عندكم": RESP_PRODUCTS_ASK,
    "وش معاكم": RESP_PRODUCTS_ASK,
    "شو عندكم": RESP_PRODUCTS_ASK,
    "شو معاكم": RESP_PRODUCTS_ASK,
    "عندكم ايش": RESP_PRODUCTS_ASK,
    "معاكم ايش": RESP_PRODUCTS_ASK,
    "ايش تبيعون": RESP_PRODUCTS_ASK,
    "ايش تبيعوا": RESP_PRODUCTS_ASK,
    "ايش تبيعو": RESP_PRODUCTS_ASK,
    "وش تبيعون": RESP_PRODUCTS_ASK,
    "وش تبيعوا": RESP_PRODUCTS_ASK,
    "وش تبيعو": RESP_PRODUCTS_ASK,
    "شو تبيعون": RESP_PRODUCTS_ASK,
    "شو تبيعوا": RESP_PRODUCTS_ASK,
    "شو تبيعو": RESP_PRODUCTS_ASK,
    "ايش منتجاتكم": RESP_PRODUCTS_ASK,
    "وش منتجاتكم": RESP_PRODUCTS_ASK,
    "شو منتجاتكم": RESP_PRODUCTS_ASK,
    "ايش بضاعتكم": RESP_PRODUCTS_ASK,
    "وش بضاعتكم": RESP_PRODUCTS_ASK,
    "ايش فيه": RESP_PRODUCTS_ASK,
    "ايش في": RESP_PRODUCTS_ASK,
    "ايش الموجود": RESP_PRODUCTS_ASK,
    "ايش المتوفر": RESP_PRODUCTS_ASK,
    "وش الموجود": RESP_PRODUCTS_ASK,
    "وش المتوفر": RESP_PRODUCTS_ASK,
    "المتوفر": RESP_PRODUCTS_ASK,
    "الموجود": RESP_PRODUCTS_ASK,
    "ابي اشوف": RESP_PRODUCTS_ASK,
    "ابي اشوف المنتجات": RESP_PRODUCTS_ASK,
    "اشتي اشوف": RESP_PRODUCTS_ASK,
    "اشتي اشوف المنتجات": RESP_PRODUCTS_ASK,
    "اريد اشوف": RESP_PRODUCTS_ASK,
    "اريد اشوف المنتجات": RESP_PRODUCTS_ASK,
    "بدي اشوف": RESP_PRODUCTS_ASK,
    "بدي اشوف المنتجات": RESP_PRODUCTS_ASK,
    "ابغى اشوف": RESP_PRODUCTS_ASK,
    "ابغى اشوف المنتجات": RESP_PRODUCTS_ASK,
    "ورني": RESP_PRODUCTS_ASK,
    "ورني المنتجات": RESP_PRODUCTS_ASK,
    "ورني البضاعه": RESP_PRODUCTS_ASK,
    "وريني": RESP_PRODUCTS_ASK,
    "وريني المنتجات": RESP_PRODUCTS_ASK,
    "عندكم شي": RESP_PRODUCTS_ASK,
    "عندكم اشياء": RESP_PRODUCTS_ASK,
    "ايش عندك": RESP_PRODUCTS_ASK,
    "وش عندك": RESP_PRODUCTS_ASK,
    "ايش معاك": RESP_PRODUCTS_ASK,
    "وش معاك": RESP_PRODUCTS_ASK,
    "ايش تبيع": RESP_PRODUCTS_ASK,
    "وش تبيع": RESP_PRODUCTS_ASK,
    "تبيعون ايش": RESP_PRODUCTS_ASK,
    "تبيعوا ايش": RESP_PRODUCTS_ASK,
    "الاسعار": RESP_PRODUCTS_ASK,
    "الأسعار": RESP_PRODUCTS_ASK,
    "اسعار": RESP_PRODUCTS_ASK,
    "أسعار": RESP_PRODUCTS_ASK,
    "كم السعر": RESP_PRODUCTS_ASK,
    "كم الاسعار": RESP_PRODUCTS_ASK,
    "كم الأسعار": RESP_PRODUCTS_ASK,
    "بكم": RESP_PRODUCTS_ASK,
    "اسعاركم": RESP_PRODUCTS_ASK,
    "أسعاركم": RESP_PRODUCTS_ASK,
    "كم سعر": RESP_PRODUCTS_ASK,
    "كم اسعار": RESP_PRODUCTS_ASK,
    "قائمة المنتجات": RESP_PRODUCTS_ASK,
    "قائمه المنتجات": RESP_PRODUCTS_ASK,
    "كتالوج": RESP_PRODUCTS_ASK,
    "الكتالوج": RESP_PRODUCTS_ASK,
    # === مكان استلام المنتج ===
    "وين تحطو البضاعه": RESP_WHERE_DELIVER,
    "وين تحطو البضاعة": RESP_WHERE_DELIVER,
    "وين تحطو المنتج": RESP_WHERE_DELIVER,
    "وين تحطون البضاعه": RESP_WHERE_DELIVER,
    "وين تحطون البضاعة": RESP_WHERE_DELIVER,
    "وين تحطون المنتج": RESP_WHERE_DELIVER,
    "وين تحطوا البضاعه": RESP_WHERE_DELIVER,
    "وين تحطوا البضاعة": RESP_WHERE_DELIVER,
    "وين تحطوا المنتج": RESP_WHERE_DELIVER,
    "وين نحطه": RESP_WHERE_DELIVER,
    "وين نحطه لك": RESP_WHERE_DELIVER,
    "وين نستلم": RESP_WHERE_DELIVER,
    "وين استلم": RESP_WHERE_DELIVER,
    "وين استلمه": RESP_WHERE_DELIVER,
    "فين تحطو البضاعه": RESP_WHERE_DELIVER,
    "فين تحطو البضاعة": RESP_WHERE_DELIVER,
    "فين تحطو المنتج": RESP_WHERE_DELIVER,
    "فين تحطون البضاعه": RESP_WHERE_DELIVER,
    "فين تحطون المنتج": RESP_WHERE_DELIVER,
    "فين نستلم": RESP_WHERE_DELIVER,
    "فين استلم": RESP_WHERE_DELIVER,
    "كيف استلم": RESP_WHERE_DELIVER,
    "كيف نستلم": RESP_WHERE_DELIVER,
    "كيف استلمه": RESP_WHERE_DELIVER,
    "كيف استلم الطلب": RESP_WHERE_DELIVER,
    "كيف استلم المنتج": RESP_WHERE_DELIVER,
    "كيف استلم البضاعه": RESP_WHERE_DELIVER,
    "مكان الاستلام": RESP_WHERE_DELIVER,
    "نقطة الاستلام": RESP_WHERE_DELIVER,
    "نقطه الاستلام": RESP_WHERE_DELIVER,
    "وين توصلون": RESP_WHERE_DELIVER,
    "وين توصلوا": RESP_WHERE_DELIVER,
    "وين توصلو": RESP_WHERE_DELIVER,
    "فين توصلون": RESP_WHERE_DELIVER,
    "فين توصلوا": RESP_WHERE_DELIVER,
    "وين اخذه": RESP_WHERE_DELIVER,
    "وين اخذ الطلب": RESP_WHERE_DELIVER,
    "فين اخذه": RESP_WHERE_DELIVER,
    "فين اخذ الطلب": RESP_WHERE_DELIVER,
    "وين الاستلام": RESP_WHERE_DELIVER,
    "فين الاستلام": RESP_WHERE_DELIVER,
    "من وين استلم": RESP_WHERE_DELIVER,
    "من فين استلم": RESP_WHERE_DELIVER,
    "وين اجي اخذه": RESP_WHERE_DELIVER,
    "وين اروح استلم": RESP_WHERE_DELIVER,
    "وين نحط لك": RESP_WHERE_DELIVER,
    "وين نحطه لكم": RESP_WHERE_DELIVER,
    "الاستلام": RESP_WHERE_DELIVER,
    "طريقة الاستلام": RESP_WHERE_DELIVER,
    "طريقه الاستلام": RESP_WHERE_DELIVER,
    # === الموقع ===
    "الموقع": RESP_LOCATION,
    "موقع": RESP_LOCATION,
    "العنوان": RESP_LOCATION,
    "عنوان": RESP_LOCATION,
    "وينكم": RESP_LOCATION,
    "وين المحل": RESP_LOCATION,
    "وين موقعكم": RESP_LOCATION,
    "فين المحل": RESP_LOCATION,
    "فين موقعكم": RESP_LOCATION,
    "المحل": RESP_LOCATION,
    "محلكم": RESP_LOCATION,
    "مكانكم": RESP_LOCATION,
    "فينكم": RESP_LOCATION,
    "وين": RESP_LOCATION,
    "فين": RESP_LOCATION,
    "الفرع": RESP_LOCATION,
    "الفروع": RESP_LOCATION,
    "فروعكم": RESP_LOCATION,
    # === الطلب ===
    "اطلب": RESP_ORDER,
    "أطلب": RESP_ORDER,
    "طلب": RESP_ORDER,
    "اريد اطلب": RESP_ORDER,
    "أريد أطلب": RESP_ORDER,
    "اريد": RESP_ORDER,
    "أريد": RESP_ORDER,
    "ابي اطلب": RESP_ORDER,
    "أبي أطلب": RESP_ORDER,
    "ابي": RESP_ORDER,
    "أبي": RESP_ORDER,
    "ابغى": RESP_ORDER,
    "أبغى": RESP_ORDER,
    "ابغا": RESP_ORDER,
    "اشتي اطلب": RESP_ORDER,
    "اشتي": RESP_ORDER,
    "بدي اطلب": RESP_ORDER,
    "بدي": RESP_ORDER,
    "طلبيه": RESP_ORDER,
    "طلبية": RESP_ORDER,
    "اطلبي": RESP_ORDER,
    # === السلام ===
    "السلام عليكم": RESP_SALAM,
    "السلام وعليكم": RESP_SALAM,
    "السلامعليكم": RESP_SALAM,
    "السلام عليكم ورحمة الله": RESP_SALAM,
    "السلام عليكم ورحمه الله": RESP_SALAM,
    "السلام عليكم ورحمة الله وبركاته": RESP_SALAM,
    "السلام عليكم ورحمه الله وبركاته": RESP_SALAM,
    "السلام": RESP_SALAM,
    "سلام": RESP_SALAM,
    "سلام عليكم": RESP_SALAM,
    "سلام وعليكم": RESP_SALAM,
    "وعليكم السلام": RESP_SALAM,
    "عليكم السلام": RESP_SALAM,
    "السلام عليكم وعليكم السلام": RESP_SALAM,
    "السلام عليك": RESP_SALAM,
    "سلام عليك": RESP_SALAM,
    "اسلام وعليكم": RESP_SALAM,
    "اسلام عليكم": RESP_SALAM,
    "اسلام": RESP_SALAM,
    "اسلام عليك": RESP_SALAM,
    "اسلام وعليك": RESP_SALAM,
    "السلام عليكم ورحمته وبركاته": RESP_SALAM,
    "اسلام عليكم ورحمة الله": RESP_SALAM,
    "اسلام عليكم ورحمه الله": RESP_SALAM,
    "اسلام عليكم ورحمة الله وبركاته": RESP_SALAM,
    # === هلا ===
    "هلا": RESP_HALA,
    "هلا والله": RESP_HALA,
    "هلا وغلا": RESP_HALA,
    "هلاا": RESP_HALA,
    "هلااا": RESP_HALA,
    "يا هلا": RESP_HALA,
    "ياهلا": RESP_HALA,
    # === مرحبا ===
    "مرحبا": RESP_MARHABA,
    "مرحبه": RESP_MARHABA,
    "مرحباً": RESP_MARHABA,
    "مرحبأ": RESP_MARHABA,
    # === كيف الحال ===
    "كيف الحال": RESP_KAIF,
    "كيف حالك": RESP_KAIF,
    "كيفك": RESP_KAIF,
    "كيفكم": RESP_KAIF,
    "شخبارك": RESP_KAIF,
    "شخباركم": RESP_KAIF,
    "شلونك": RESP_KAIF,
    "شلونكم": RESP_KAIF,
    "اخبارك": RESP_KAIF,
    "أخبارك": RESP_KAIF,
    "اشلونك": RESP_KAIF,
    "وش اخبارك": RESP_KAIF,
    "وش أخبارك": RESP_KAIF,
    "ايش اخبارك": RESP_KAIF,
    # === اهلا ===
    "اهلا": RESP_AHLAN,
    "اهلين": RESP_AHLAN,
    "أهلا": RESP_AHLAN,
    "أهلين": RESP_AHLAN,
    "اهلاً": RESP_AHLAN,
    "أهلاً": RESP_AHLAN,
    "حياك": RESP_AHLAN,
    "حياك الله": RESP_AHLAN,
    "حياكم": RESP_AHLAN,
    "حياكم الله": RESP_AHLAN,
    # === هاي ===
    "هاي": RESP_HAI,
    "هااي": RESP_HAI,
    "hi": RESP_HAI,
    "Hi": RESP_HAI,
    "hello": RESP_HAI,
    "Hello": RESP_HAI,
    "hey": RESP_HAI,
    "Hey": RESP_HAI,
    # === مساء الخير ===
    "مساء الخير": RESP_MASA,
    "مسا الخير": RESP_MASA,
    "مساءالخير": RESP_MASA,
    "مساء الخير عليكم": RESP_MASA,
    "مسائكم خير": RESP_MASA,
    "مساكم الله بالخير": RESP_MASA,
    # === صباح الخير ===
    "صباح الخير": RESP_SABAH,
    "صباحالخير": RESP_SABAH,
    "صباح الخير عليكم": RESP_SABAH,
    "صباح النور": RESP_SABAH,
    "صباحكم خير": RESP_SABAH,
    # === يعطيك العافية ===
    "يعطيك العافيه": RESP_AFYA,
    "يعطيك العافية": RESP_AFYA,
    "الله يعافيك": RESP_AFYA,
    "الله يعافيكم": RESP_AFYA,
    "يعطيكم العافيه": RESP_AFYA,
    "يعطيكم العافية": RESP_AFYA,
    "عافيه": RESP_AFYA,
    "عافية": RESP_AFYA,
    # === شكرا ===
    "شكرا": RESP_SHUKR,
    "شكراً": RESP_SHUKR,
    "شكرا لك": RESP_SHUKR,
    "شكراً لك": RESP_SHUKR,
    "شكرا لكم": RESP_SHUKR,
    "مشكور": RESP_SHUKR,
    "مشكوره": RESP_SHUKR,
    "مشكورة": RESP_SHUKR,
    "مشكورين": RESP_SHUKR,
    "جزاك الله خير": RESP_SHUKR,
    "جزاكم الله خير": RESP_SHUKR,
    "جزاك الله خيرا": RESP_SHUKR,
    "جزاك الله خيراً": RESP_SHUKR,
    "تسلم": RESP_SHUKR,
    "تسلمي": RESP_SHUKR,
    "تسلمين": RESP_SHUKR,
    "يسلمو": RESP_SHUKR,
    "الله يجزاك خير": RESP_SHUKR,
}

# Keywords that trigger image responses
QUDOR_KEYWORDS = ["قدور", "القدور", "قدر", "القدر", "طقم قدور", "طقم القدور", "قدور المائدة", "قدور المائده", "قدور هندي", "قدور ستانلس", "طقم"]
THALAJA_KEYWORDS = ["ثلاجة", "ثلاجه", "الثلاجة", "الثلاجه", "شاي", "ثلاجة شاي", "ثلاجه شاي", "ثلاجة الشاي", "ثلاجه الشاي", "ترمس", "ترمز", "حافظة", "حافظه"]
FARAMA_KEYWORDS = ["فرامة", "فرامه", "الفرامة", "الفرامه", "فرامة الضغطة", "فرامه الضغطه", "فرامة الضغطه", "فرامه الضغطة", "الفرامة الذكية", "الفرامه الذكيه", "فرامة ذكية", "فرامه ذكيه", "عصارة", "عصاره", "العصارة", "العصاره", "فرامة المائدة", "فرامه المائده", "فرامة المائده", "فرامه المائدة", "فرامة خضار", "فرامه خضار", "قطاعة", "قطاعه", "القطاعة", "القطاعه", "مفرمة", "مفرمه", "المفرمة", "المفرمه", "خلاط", "الخلاط", "فرامة ضغطة", "فرامه ضغطه", "ضغطة ذكية", "ضغطه ذكيه"]

WELCOME_MESSAGE = """يا غالية خلينا بموضوعنا 😊✨
إحنا محل *Titiz* للأدوات المنزلية 🏠

عندنا منتجات حلوة وأسعار تناسب الجميع 👌
والتوصيل مجاني لباب بيتكِ! 🚚

اكتبي *قدور* أو *ثلاجة* وشوفي الصور والأسعار 😍
أو اكتبي *1* لكل المنتجات"""


def send_message(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def send_image(to, image_url, caption=""):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def send_image_by_id(to, media_id, caption=""):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def notify_owner(sender, msg_body):
    """إرسال إشعار للمالك بأن زبون راسل البوت"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    notification = f"📩 *رسالة جديدة من زبون*\n\n👤 الرقم: {sender}\n💬 الرسالة: {msg_body}\n🕐 الوقت: {now}\n\nللرد عليه مباشرة: wa.me/{sender}"
    send_message(OWNER_NUMBER, notification)


def add_customer(sender, msg_body):
    """إضافة الزبون للقائمة"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # تحقق إذا الرقم موجود مسبقاً
    for c in customers:
        if c["number"] == sender:
            c["last_message"] = msg_body
            c["last_time"] = now
            c["messages_count"] += 1
            return
    # زبون جديد
    customers.append({
        "number": sender,
        "first_message": msg_body,
        "last_message": msg_body,
        "first_time": now,
        "last_time": now,
        "messages_count": 1
    })


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def handle_message():
    data = request.get_json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        if "messages" in value:
            message = value["messages"][0]
            sender = message["from"]
            msg_body = message.get("text", {}).get("body", "").strip()

            # لا ترسل إشعار لنفسك
            if sender != OWNER_NUMBER:
                # إضافة الزبون للقائمة
                add_customer(sender, msg_body)
                # إشعار المالك
                notify_owner(sender, msg_body)

            # أمر خاص للمالك: الرد على زبون من رقم البوت
            if sender == OWNER_NUMBER and msg_body.startswith("رد "):
                parts = msg_body.split(" ", 2)
                if len(parts) == 3:
                    target_number = parts[1]
                    reply_text = parts[2]
                    send_message(target_number, reply_text)
                    send_message(OWNER_NUMBER, f"✅ تم إرسال ردك للزبون {target_number}")
                else:
                    send_message(OWNER_NUMBER, "❌ الصيغة: رد [رقم الزبون] [الرسالة]\nمثال: رد 967777123456 طلبك جاهز")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: إضافة منتج جديد
            if sender == OWNER_NUMBER and msg_body.startswith("اضف "):
                parts = msg_body.split(" ", 3)
                if len(parts) >= 3:
                    product_name = parts[1]
                    product_price = parts[2]
                    product_desc = parts[3] if len(parts) == 4 else ""
                    custom_products[product_name] = {
                        "name": product_name,
                        "price": product_price,
                        "description": product_desc,
                        "image_id": "",
                        "added": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    save_products(custom_products)
                    send_message(OWNER_NUMBER, f"✅ تم إضافة المنتج: {product_name}\nالسعر: {product_price} ريال\nالوصف: {product_desc}\n\nلإضافة صورة: أرسل صورة مع كابشن فيه اسم المنتج")
                else:
                    send_message(OWNER_NUMBER, "❌ الصيغة: اضف [اسم المنتج] [السعر] [الوصف]\nمثال: اضف ملعقة 500 ملعقة ستانلس ثقيلة")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: تعديل سعر منتج
            if sender == OWNER_NUMBER and msg_body.startswith("عدل سعر "):
                parts = msg_body.split(" ", 3)
                if len(parts) == 4:
                    product_name = parts[2]
                    new_price = parts[3]
                    if product_name in custom_products:
                        custom_products[product_name]["price"] = new_price
                        save_products(custom_products)
                        send_message(OWNER_NUMBER, f"✅ تم تعديل سعر {product_name} إلى {new_price} ريال")
                    else:
                        send_message(OWNER_NUMBER, f"❌ المنتج '{product_name}' غير موجود")
                else:
                    send_message(OWNER_NUMBER, "❌ الصيغة: عدل سعر [اسم المنتج] [السعر الجديد]\nمثال: عدل سعر ملعقة 600")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: حذف منتج
            if sender == OWNER_NUMBER and msg_body.startswith("حذف "):
                product_name = msg_body.replace("حذف ", "").strip()
                if product_name in custom_products:
                    del custom_products[product_name]
                    save_products(custom_products)
                    send_message(OWNER_NUMBER, f"✅ تم حذف المنتج: {product_name}")
                else:
                    send_message(OWNER_NUMBER, f"❌ المنتج '{product_name}' غير موجود")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: عرض المخزن
            if sender == OWNER_NUMBER and msg_body in ["المخزن", "مخزن", "منتجاتي"]:
                if custom_products:
                    product_list = "📦 *المنتجات المحفوظة:*\n\n"
                    for i, (name, info) in enumerate(custom_products.items(), 1):
                        has_img = "🖼️" if info.get("image_id") else "❌"
                        product_list += f"{i}. *{name}* - {info['price']} ريال {has_img}\n"
                        if info.get('description'):
                            product_list += f"   {info['description']}\n"
                    product_list += f"\n📊 إجمالي: {len(custom_products)} منتج"
                    send_message(OWNER_NUMBER, product_list)
                else:
                    send_message(OWNER_NUMBER, "📦 المخزن فارغ. أضف منتجات بالأمر:\nاضف [اسم] [سعر] [وصف]")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: رفع صورة لمنتج
            if sender == OWNER_NUMBER and message.get("type") == "image":
                image_info = message.get("image", {})
                media_id = image_info.get("id", "")
                caption = image_info.get("caption", "").strip()
                if caption and media_id:
                    if caption in custom_products:
                        custom_products[caption]["image_id"] = media_id
                        save_products(custom_products)
                        send_message(OWNER_NUMBER, f"✅ تم إضافة صورة للمنتج: {caption}")
                    else:
                        # إضافة منتج جديد بالصورة
                        custom_products[caption] = {
                            "name": caption,
                            "price": "0",
                            "description": "",
                            "image_id": media_id,
                            "added": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        save_products(custom_products)
                        send_message(OWNER_NUMBER, f"✅ تم حفظ الصورة كمنتج جديد: {caption}\nعدل السعر بالأمر:\nعدل سعر {caption} [السعر]")
                elif media_id and not caption:
                    send_message(OWNER_NUMBER, "❌ أرسل الصورة مع كابشن فيه اسم المنتج")
                return jsonify({"status": "ok"}), 200

            # أمر خاص للمالك: عرض قائمة الزبائن
            if sender == OWNER_NUMBER and msg_body == "الزبائن":
                if customers:
                    customer_list = "📋 *قائمة الزبائن:*\n\n"
                    for i, c in enumerate(customers, 1):
                        customer_list += f"{i}. 👤 {c['number']}\n"
                        customer_list += f"   آخر رسالة: {c['last_message']}\n"
                        customer_list += f"   الوقت: {c['last_time']}\n"
                        customer_list += f"   عدد الرسائل: {c['messages_count']}\n\n"
                    customer_list += f"📊 إجمالي الزبائن: {len(customers)}"
                    send_message(sender, customer_list)
                else:
                    send_message(sender, "📋 لا يوجد زبائن حتى الآن.")
                return jsonify({"status": "ok"}), 200

            # تطبيع النص - إزالة الرموز والمسافات الزائدة
            msg_normalized = msg_body.lower().strip()
            # إزالة علامات الترقيم والرموز
            for ch in ['!', '?', '.', ',', '؟', '،', '\u200f', '\u200e']:
                msg_normalized = msg_normalized.replace(ch, '')
            msg_normalized = msg_normalized.strip()

            # الرد التلقائي - مطابقة مباشرة
            matched_key = None
            if msg_normalized in RESPONSES:
                matched_key = msg_normalized
            elif msg_body in RESPONSES:
                matched_key = msg_body
            else:
                # بحث جزئي - لو الرسالة تحتوي على كلمة مفتاحية
                for key in RESPONSES:
                    if len(key) > 2 and key in msg_normalized:
                        matched_key = key
                        break

            if matched_key:
                reply = RESPONSES[matched_key]
                # ردود منفصلة (قائمة)
                if isinstance(reply, list):
                    for r in reply:
                        send_message(sender, r)
                # صورة + نص - الفرامة (3 صور)
                elif matched_key in FARAMA_KEYWORDS:
                    send_message(sender, reply)
                    send_image_by_id(sender, IMG_FARAMA_BIG, "🔴 الكبير MD-5266 - 3,000 ريال")
                    send_image_by_id(sender, IMG_FARAMA_MED, "🟢 الوسط MD-5076 - 2,500 ريال")
                    send_image_by_id(sender, IMG_FARAMA_SML, "🟢 الصغير MD-5066 - 2,000 ريال")
                # صورة + نص - القدور
                elif matched_key in QUDOR_KEYWORDS:
                    send_image(sender, IMG_QUDOR, reply)
                elif matched_key in THALAJA_KEYWORDS:
                    send_image(sender, IMG_THALAJA, reply)
                else:
                    send_message(sender, reply)
            else:
                # البحث في المنتجات المخصصة (المضافة من المالك)
                found_product = None
                for pname, pinfo in custom_products.items():
                    if pname in msg_normalized or msg_normalized in pname:
                        found_product = pinfo
                        break
                if found_product:
                    product_reply = f"📦 *{found_product['name']}*\n\n"
                    if found_product.get('description'):
                        product_reply += f"{found_product['description']}\n\n"
                    product_reply += f"💰 السعر: {found_product['price']} ريال\n"
                    product_reply += f"🚚 التوصيل مجاني داخل المحافظة!\n\nاكتبي *اطلب* للطلب 😍"
                    if found_product.get('image_id'):
                        send_image_by_id(sender, found_product['image_id'], product_reply)
                    else:
                        send_message(sender, product_reply)
                else:
                    send_message(sender, WELCOME_MESSAGE)
    except (KeyError, IndexError):
        pass
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
    return "✅ بوت Titiz للأدوات المنزلية يعمل بنجاح!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
