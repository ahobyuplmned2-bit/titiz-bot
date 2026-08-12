"""
نظام أوامر الإدارة
"""

from database import (
    get_order, update_order_status, get_customer, add_product,
    get_all_products, log_action, get_statistics
)
from payment_system import PaymentManager
import json

class AdminCommands:
    """فئة لمعالجة أوامر الإدارة"""
    
    ADMIN_NUMBERS = ["967773595571"]  # أرقام الإدارة المصرح لهم
    
    @staticmethod
    def is_admin(phone_number):
        """التحقق من أن المستخدم إدارة"""
        return phone_number in AdminCommands.ADMIN_NUMBERS
    
    @staticmethod
    def parse_command(message_text):
        """تحليل أمر الإدارة"""
        parts = message_text.strip().split()
        if not parts:
            return None, []
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    @staticmethod
    def handle_orders_command(args):
        """أمر: عرض الطلبات"""
        message = "📦 *الطلبات الحالية:*\n\n"
        message += "هذه الميزة قيد التطوير\n"
        message += "سيتم عرض جميع الطلبات هنا قريباً"
        return message
    
    @staticmethod
    def handle_order_details(order_number):
        """أمر: تفاصيل الطلب"""
        order = get_order(order_number)
        
        if not order:
            return f"❌ لم أجد الطلب: {order_number}"
        
        message = f"📦 *تفاصيل الطلب: {order_number}*\n\n"
        message += f"👤 العميل: {order.get('customer_name', 'غير محدد')}\n"
        message += f"📞 الهاتف: {order.get('phone_number', 'غير محدد')}\n"
        message += f"📍 العنوان: {order.get('address', 'غير محدد')}\n"
        message += f"💳 طريقة الدفع: {order.get('payment_method', 'غير محدد')}\n"
        message += f"📊 الحالة: {order.get('order_status', 'غير محدد')}\n\n"
        
        message += "🛍️ *المنتجات:*\n"
        for product in order.get('products_data', []):
            message += f"• {product['name']} × {product['quantity']} = {product['price'] * product['quantity']} ريال\n"
        
        message += f"\n💰 *الإجمالي: {order['total_price']} ريال*"
        
        return message
    
    @staticmethod
    def handle_update_order_status(order_number, new_status):
        """أمر: تحديث حالة الطلب"""
        valid_statuses = [
            'جديد', 'بانتظار مراجعة الدفع', 'تم الدفع',
            'جاري التجهيز', 'تم الشحن', 'تم التسليم', 'ملغي'
        ]
        
        if new_status not in valid_statuses:
            return f"❌ حالة غير صحيحة\n\nالحالات المتاحة: {', '.join(valid_statuses)}"
        
        update_order_status(order_number, new_status)
        log_action('admin', None, 'update_order_status', f'Order: {order_number}, Status: {new_status}')
        
        return f"✅ تم تحديث حالة الطلب {order_number} إلى: {new_status}"
    
    @staticmethod
    def handle_confirm_payment(order_number):
        """أمر: تأكيد الدفع"""
        order = get_order(order_number)
        
        if not order:
            return f"❌ لم أجد الطلب: {order_number}"
        
        if order['payment_method'] not in {'التحويل المسبق', 'تحويل مسبق'}:
            return f"❌ هذا الطلب لا يحتاج تأكيد دفع (طريقة الدفع: {order['payment_method']})"

        if not order.get('payment_proof_url'):
            return "❌ لا يمكن تأكيد الدفع قبل حفظ صورة إشعار التحويل مع الطلب."
        
        confirmed = PaymentManager.confirm_transfer_payment(order_number)
        if not confirmed:
            return f"❌ تعذر تحديث حالة الطلب {order_number}"
        
        message = f"✅ تم تأكيد الدفع للطلب {order_number}\n\n"
        message += "سيتم إرسال إشعار للعميل بتأكيد الدفع"
        
        return message
    
    @staticmethod
    def handle_add_product(args):
        """أمر: إضافة منتج جديد"""
        if len(args) < 3:
            return "❌ الصيغة الصحيحة: اضف منتج [الاسم] [السعر] [الوصف]"
        
        name = args[0]
        try:
            price = float(args[1])
        except ValueError:
            return "❌ السعر يجب أن يكون رقماً"
        
        description = ' '.join(args[2:])
        
        product_id = add_product(name, price, description)
        
        if product_id:
            return f"✅ تم إضافة المنتج: {name}\n💰 السعر: {price} ريال"
        else:
            return f"❌ المنتج {name} موجود بالفعل"
    
    @staticmethod
    def handle_list_products():
        """أمر: عرض جميع المنتجات"""
        products = get_all_products()
        
        if not products:
            return "❌ لا توجد منتجات"
        
        message = "📦 *قائمة المنتجات:*\n\n"
        for idx, product in enumerate(products, 1):
            message += f"{idx}. {product['name']}\n"
            message += f"   💰 السعر: {product['price']} ريال\n"
            message += f"   📊 الكمية: {product.get('quantity', 0)}\n\n"
        
        return message
    
    @staticmethod
    def handle_statistics():
        """أمر: الإحصائيات"""
        stats = get_statistics()
        
        message = "📊 *الإحصائيات:*\n\n"
        message += f"💰 إجمالي المبيعات: {stats['total_sales']} ريال\n"
        message += f"📦 عدد الطلبات: {stats['total_orders']}\n"
        message += f"👥 عدد العملاء: {stats['total_customers']}\n\n"
        
        if stats['top_products']:
            message += "🏆 *أكثر المنتجات مبيعاً:*\n"
            for product in stats['top_products'][:5]:
                message += f"• {product['name']}: {product.get('total_sold', 0)} وحدة\n"
        
        return message
    
    @staticmethod
    def handle_help():
        """أمر: المساعدة"""
        message = "📋 *أوامر الإدارة:*\n\n"
        message += "🛍️ *الطلبات:*\n"
        message += "• الطلبات - عرض جميع الطلبات\n"
        message += "• تفاصيل [رقم] - عرض تفاصيل طلب\n"
        message += "• حالة [رقم] [الحالة] - تحديث حالة الطلب\n"
        message += "• تأكيد دفع [رقم] - تأكيد دفع التحويل\n\n"
        
        message += "📦 *المنتجات:*\n"
        message += "• المنتجات - عرض جميع المنتجات\n"
        message += "• اضف منتج [الاسم] [السعر] [الوصف]\n\n"
        
        message += "📊 *الإحصائيات:*\n"
        message += "• إحصائيات - عرض الإحصائيات العامة\n"
        
        return message

def process_admin_command(phone_number, message_text):
    """معالجة أمر الإدارة"""
    
    if not AdminCommands.is_admin(phone_number):
        return "❌ ليس لديك صلاحيات الإدارة"
    
    command, args = AdminCommands.parse_command(message_text)
    
    if not command:
        return AdminCommands.handle_help()
    
    # معالجة الأوامر المختلفة
    if command == "الطلبات":
        return AdminCommands.handle_orders_command(args)
    
    elif command == "تفاصيل" and args:
        return AdminCommands.handle_order_details(args[0])
    
    elif command == "حالة" and len(args) >= 2:
        return AdminCommands.handle_update_order_status(args[0], ' '.join(args[1:]))
    
    elif command == "تأكيد" and len(args) >= 2 and args[0] == "دفع":
        return AdminCommands.handle_confirm_payment(args[1])
    
    elif command == "اضف" and args and args[0] == "منتج":
        return AdminCommands.handle_add_product(args[1:])
    
    elif command == "المنتجات":
        return AdminCommands.handle_list_products()
    
    elif command == "إحصائيات":
        return AdminCommands.handle_statistics()
    
    elif command == "مساعدة" or command == "help":
        return AdminCommands.handle_help()
    
    else:
        return f"❌ أمر غير معروف: {command}\n\nاكتب 'مساعدة' لعرض الأوامر المتاحة"
