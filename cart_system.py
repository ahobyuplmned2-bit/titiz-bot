"""
نظام إدارة السلة والطلبات
"""

from database import (
    add_to_cart, get_cart, clear_cart, remove_from_cart, 
    update_cart_quantity, create_order, get_order, 
    update_order_status, get_customer, add_customer, get_product
)
import json

class CartManager:
    """مدير السلة"""
    
    @staticmethod
    def add_product(phone_number, product_id, quantity=1):
        """إضافة منتج إلى السلة"""
        add_to_cart(phone_number, product_id, quantity)
        return True
    
    @staticmethod
    def get_cart_items(phone_number):
        """الحصول على عناصر السلة"""
        return get_cart(phone_number)
    
    @staticmethod
    def get_cart_summary(phone_number):
        """الحصول على ملخص السلة"""
        items = get_cart(phone_number)
        
        total_price = 0
        total_items = 0
        
        for item in items:
            item_total = item['price'] * item['quantity']
            total_price += item_total
            total_items += item['quantity']
        
        return {
            'items': items,
            'total_price': total_price,
            'total_items': total_items,
            'item_count': len(items)
        }
    
    @staticmethod
    def update_quantity(phone_number, product_id, quantity):
        """تحديث كمية المنتج"""
        update_cart_quantity(phone_number, product_id, quantity)
        return True
    
    @staticmethod
    def remove_product(phone_number, product_id):
        """حذف منتج من السلة"""
        remove_from_cart(phone_number, product_id)
        return True
    
    @staticmethod
    def clear(phone_number):
        """تفريغ السلة"""
        clear_cart(phone_number)
        return True

class OrderManager:
    """مدير الطلبات"""
    
    @staticmethod
    def create_from_cart(phone_number, customer_name, customer_address, payment_method):
        """إنشاء طلب من السلة"""
        
        # الحصول على بيانات العميل أو إضافته
        customer = get_customer(phone_number)
        if not customer:
            add_customer(phone_number, customer_name, customer_address)
            customer = get_customer(phone_number)
        
        customer_id = customer['id']
        
        # الحصول على عناصر السلة
        cart_items = get_cart(phone_number)
        
        if not cart_items:
            return None, "السلة فارغة"
        
        # حساب السعر الإجمالي
        products_data = []
        total_price = 0
        
        for item in cart_items:
            product_data = {
                'product_id': item['product_id'],
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'image_id': item['image_id']
            }
            products_data.append(product_data)
            total_price += item['price'] * item['quantity']
        
        # إنشاء الطلب
        order_number, order_id = create_order(
            customer_id, 
            products_data, 
            total_price, 
            payment_method
        )
        
        # تفريغ السلة
        clear_cart(phone_number)
        
        return order_number, total_price
    
    @staticmethod
    def get_order_details(order_number):
        """الحصول على تفاصيل الطلب"""
        return get_order(order_number)
    
    @staticmethod
    def update_status(order_number, new_status):
        """تحديث حالة الطلب"""
        update_order_status(order_number, new_status)
        return True
    
    @staticmethod
    def format_order_message(order_data):
        """تنسيق رسالة الطلب للإرسال"""
        
        message = f"📦 *تفاصيل الطلب: {order_data['order_number']}*\n\n"
        message += f"👤 العميل: {order_data.get('customer_name', 'غير محدد')}\n"
        message += f"📞 الهاتف: {order_data.get('phone_number', 'غير محدد')}\n"
        message += f"📍 العنوان: {order_data.get('address', 'غير محدد')}\n\n"
        
        message += "🛍️ *المنتجات:*\n"
        
        for product in order_data['products_data']:
            message += f"• {product['name']}\n"
            message += f"  السعر: {product['price']} ريال × {product['quantity']} = {product['price'] * product['quantity']} ريال\n"
        
        message += f"\n💰 *الإجمالي: {order_data['total_price']} ريال*\n"
        message += f"💳 *طريقة الدفع: {order_data['payment_method']}*\n"
        message += f"📊 *الحالة: {order_data['order_status']}*\n"
        
        return message

def format_cart_message(cart_summary):
    """تنسيق رسالة السلة"""
    
    if not cart_summary['items']:
        return "🛒 السلة فارغة حالياً\n\nاكتبي *تصفح* لاستعراض المنتجات 😊"
    
    message = "🛒 *سلتك الحالية:*\n\n"
    
    for idx, item in enumerate(cart_summary['items'], 1):
        message += f"{idx}. {item['name']}\n"
        message += f"   السعر: {item['price']} ريال × {item['quantity']} = {item['price'] * item['quantity']} ريال\n"
    
    message += f"\n{'='*40}\n"
    message += f"📊 عدد المنتجات: {cart_summary['total_items']}\n"
    message += f"💰 الإجمالي: {cart_summary['total_price']} ريال\n"
    message += f"\n✅ اكتبي *اكمل الطلب* لإتمام الشراء\n"
    message += f"🔄 اكتبي *متابعة التسوق* للعودة للمنتجات\n"
    message += f"🗑️ اكتبي *فرغ السلة* لحذف جميع المنتجات"
    
    return message
