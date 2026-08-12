"""
نظام إدارة الدفع والتحويلات
"""

from database import update_order_status, update_order_payment_proof, get_order, log_action
import json

PAYMENT_METHODS = {
    'cod': 'الدفع عند الاستلام',
    'transfer': 'التحويل المسبق'
}

TRANSFER_ACCOUNTS = {
    'jeeb': {
        'name': 'نقطة جيب',
        'account': '906072',
        'emoji': '🟢'
    },
    'krimi_card': {
        'name': 'الكريمي نقطة حاسب',
        'account': '1202686',
        'emoji': '🟡'
    },
    'krimi_deposit': {
        'name': 'إيداع عبر الكريمي',
        'account': '3122678098',
        'emoji': '🏦'
    }
}

class PaymentManager:
    """مدير نظام الدفع"""
    
    @staticmethod
    def get_payment_methods_message():
        """الحصول على رسالة طرق الدفع"""
        
        message = "💳 *طرق الدفع المتاحة:*\n\n"
        
        message += "✅ *الدفع عند الاستلام*\n"
        message += "نحط الطلب لأقرب نقطة منك وتدفعي وقت الاستلام 👌\n\n"
        
        message += "✅ *التحويل المسبق*\n"
        message += "تدفعي أولاً ثم يتم توصيل الطلب لباب المنزل 🚚\n\n"
        
        message += "💰 *حسابات التحويل:*\n\n"
        
        for key, account in TRANSFER_ACCOUNTS.items():
            message += f"{account['emoji']} *{account['name']}:*\n"
            message += f"`{account['account']}`\n\n"
        
        message += "اختاري طريقة الدفع:\n"
        message += "اكتبي: *1* للدفع عند الاستلام\n"
        message += "اكتبي: *2* للتحويل المسبق"
        
        return message
    
    @staticmethod
    def process_cod_payment(order_number):
        """معالجة الدفع عند الاستلام"""
        update_order_status(order_number, 'جديد')
        log_action('payment', None, 'cod_payment', f'Order: {order_number}')
        
        message = f"✅ *تم تأكيد طلبك بنجاح!*\n\n"
        message += f"📦 رقم الطلب: {order_number}\n"
        message += f"💳 طريقة الدفع: الدفع عند الاستلام\n\n"
        message += "سيتم توصيل طلبك قريباً وتدفعي عند الاستلام 👌\n"
        message += "سنتواصل معك قريباً بتفاصيل التوصيل 📞"
        
        return message
    
    @staticmethod
    def get_transfer_payment_message():
        """الحصول على رسالة التحويل المسبق"""
        
        message = "🏦 *التحويل المسبق*\n\n"
        message += "يرجى التحويل إلى أحد الحسابات التالية:\n\n"
        
        for key, account in TRANSFER_ACCOUNTS.items():
            message += f"{account['emoji']} *{account['name']}:*\n"
            message += f"`{account['account']}`\n\n"
        
        message += "⚠️ *بعد التحويل:*\n"
        message += "أرسلي صورة إشعار التحويل أو الإيصال\n"
        message += "سيتم التحقق من الدفع وتجهيز طلبك قريباً ✅"
        
        return message
    
    @staticmethod
    def process_transfer_payment(order_number, proof_url=None):
        """معالجة التحويل المسبق"""
        if proof_url:
            update_order_payment_proof(order_number, proof_url)
        else:
            update_order_status(order_number, 'بانتظار مراجعة الدفع')
        
        details = f'Order: {order_number}'
        if proof_url:
            details += f', Proof: {proof_url}'
        
        log_action('payment', None, 'transfer_payment', details)
        
        message = f"✅ *تم استلام إشعار التحويل*\n\n"
        message += f"📦 رقم الطلب: {order_number}\n"
        message += "📊 الحالة: بانتظار مراجعة الدفع\n\n"
        message += "سيتم التحقق من الدفع في أسرع وقت ممكن ⏳\n"
        message += "سنخبرك عندما يتم تأكيد الدفع 📞"
        
        return message
    
    @staticmethod
    def confirm_transfer_payment(order_number):
        """تأكيد التحويل من قبل الإدارة"""
        updated = update_order_status(order_number, 'تم الدفع')
        log_action('payment', None, 'payment_confirmed', f'Order: {order_number}')
        
        return updated
    
    @staticmethod
    def get_admin_payment_confirmation_message(order_number):
        """رسالة تأكيد الدفع للعميل"""
        
        return "تم استلام دفعتك بنجاح وسيتم تجهيز طلبك قريبًا."

def format_payment_proof_message(order_number, phone_number):
    """تنسيق رسالة طلب إثبات الدفع"""
    
    message = f"📸 *يرجى إرسال صورة إشعار التحويل*\n\n"
    message += f"📦 رقم الطلب: {order_number}\n"
    message += f"📞 رقم الهاتف: {phone_number}\n\n"
    message += "الصورة ستساعدنا في التحقق السريع من الدفع ✅"
    
    return message
