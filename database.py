"""
نظام إدارة قاعدة البيانات للمشروع
يدعم SQLite للتطوير و PostgreSQL للإنتاج
"""

import sqlite3
import os
import json
from datetime import datetime
from threading import Lock

# قفل للتعامل الآمن مع قاعدة البيانات
db_lock = Lock()

# اختيار نوع قاعدة البيانات
USE_SQLITE = True
DB_PATH = "titiz_bot.db"

def init_db():
    """إنشاء جداول قاعدة البيانات"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # جدول العملاء
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                name TEXT,
                address TEXT,
                first_order_date TIMESTAMP,
                order_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الطلبات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                products_data TEXT NOT NULL,
                total_price REAL NOT NULL,
                payment_method TEXT,
                payment_proof_url TEXT,
                order_status TEXT DEFAULT 'جديد',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        ''')
        
        # جدول المنتجات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                image_id TEXT,
                quantity INTEGER DEFAULT 0,
                available BOOLEAN DEFAULT 1,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول السلة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # جدول جلسات المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                session_data TEXT,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الأسئلة والأجوبة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE NOT NULL,
                answer TEXT NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول السجلات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT,
                phone_number TEXT,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الكلمات المفتاحية
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, keyword)
            )
        ''')

        # ترقية آمنة لقواعد البيانات القديمة دون حذف أي بيانات موجودة.
        migrations = {
            "customers": {
                "first_order_date": "TIMESTAMP",
                "order_count": "INTEGER DEFAULT 0",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            "orders": {
                "payment_proof_url": "TEXT",
                "order_status": "TEXT DEFAULT 'جديد'",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        }
        for table, columns in migrations.items():
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {row[1] for row in cursor.fetchall()}
            for column, definition in columns.items():
                if column not in existing_columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        
        conn.commit()
        conn.close()

def add_customer(phone_number, name=None, address=None):
    """إضافة أو تحديث عميل"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO customers (phone_number, name, address)
                VALUES (?, ?, ?)
            ''', (phone_number, name, address))
            conn.commit()
        except sqlite3.IntegrityError:
            # العميل موجود بالفعل
            if name or address:
                cursor.execute('''
                    UPDATE customers 
                    SET name = COALESCE(?, name), 
                        address = COALESCE(?, address),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE phone_number = ?
                ''', (name, address, phone_number))
                conn.commit()
        
        conn.close()

def get_customer(phone_number):
    """الحصول على بيانات العميل"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM customers WHERE phone_number = ?', (phone_number,))
        customer = cursor.fetchone()
        conn.close()
        
        return dict(customer) if customer else None

def add_to_cart(phone_number, product_id, quantity=1):
    """إضافة منتج إلى السلة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, quantity FROM cart 
            WHERE phone_number = ? AND product_id = ?
        ''', (phone_number, product_id))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE cart SET quantity = quantity + ? 
                WHERE phone_number = ? AND product_id = ?
            ''', (quantity, phone_number, product_id))
        else:
            cursor.execute('''
                INSERT INTO cart (phone_number, product_id, quantity)
                VALUES (?, ?, ?)
            ''', (phone_number, product_id, quantity))
        
        conn.commit()
        conn.close()

def get_cart(phone_number):
    """الحصول على سلة العميل"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.image_id
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.phone_number = ?
        ''', (phone_number,))
        
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return items

def clear_cart(phone_number):
    """تفريغ السلة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM cart WHERE phone_number = ?', (phone_number,))
        conn.commit()
        conn.close()

def save_user_session(phone_number, state=None, session_data=None):
    """حفظ حالة المحادثة وسياقها ليستمر بعد إعادة التشغيل أو العودة لاحقاً."""
    payload = {"state": state, "data": session_data or {}}
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO user_sessions (phone_number, session_data, last_activity)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET
                session_data = excluded.session_data,
                last_activity = CURRENT_TIMESTAMP
        ''', (phone_number, json.dumps(payload, ensure_ascii=False)))
        conn.commit()
        conn.close()

def load_user_session(phone_number):
    """استعادة آخر حالة وسياق محفوظ للعميل."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            'SELECT session_data, last_activity FROM user_sessions WHERE phone_number = ?',
            (phone_number,)
        ).fetchone()
        conn.close()
    if not row:
        return None
    try:
        data = json.loads(row["session_data"] or "{}")
        data["last_activity"] = row["last_activity"]
        return data
    except (TypeError, json.JSONDecodeError):
        return None

def delete_user_session(phone_number):
    """حذف جلسة العميل عند الإلغاء أو اكتمال الطلب."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM user_sessions WHERE phone_number = ?', (phone_number,))
        conn.commit()
        conn.close()

def remove_from_cart(phone_number, product_id):
    """حذف منتج من السلة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM cart 
            WHERE phone_number = ? AND product_id = ?
        ''', (phone_number, product_id))
        
        conn.commit()
        conn.close()

def update_cart_quantity(phone_number, product_id, quantity):
    """تحديث كمية المنتج في السلة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if quantity <= 0:
            cursor.execute('''
                DELETE FROM cart 
                WHERE phone_number = ? AND product_id = ?
            ''', (phone_number, product_id))
        else:
            cursor.execute('''
                UPDATE cart SET quantity = ? 
                WHERE phone_number = ? AND product_id = ?
            ''', (quantity, phone_number, product_id))
        
        conn.commit()
        conn.close()

def create_order(customer_id, products_data, total_price, payment_method):
    """إنشاء طلب جديد"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # إنشاء رقم الطلب
        cursor.execute('SELECT COUNT(*) FROM orders')
        order_count = cursor.fetchone()[0] + 1
        order_number = f"ORD-{order_count:06d}"
        
        cursor.execute('''
            INSERT INTO orders (order_number, customer_id, products_data, total_price, payment_method, order_status)
            VALUES (?, ?, ?, ?, ?, 'جديد')
        ''', (order_number, customer_id, json.dumps(products_data, ensure_ascii=False), total_price, payment_method))
        
        order_id = cursor.lastrowid
        
        # تحديث عدد الطلبات للعميل
        cursor.execute('''
            UPDATE customers 
            SET order_count = order_count + 1,
                first_order_date = COALESCE(first_order_date, CURRENT_TIMESTAMP)
            WHERE id = ?
        ''', (customer_id,))
        
        conn.commit()
        conn.close()
        
        return order_number, order_id

def get_order(order_number):
    """الحصول على بيانات الطلب"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.*, c.phone_number, c.name AS customer_name, c.address
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.order_number = ?
        ''', (order_number,))
        order = cursor.fetchone()
        conn.close()
        
        if order:
            order_dict = dict(order)
            order_dict['products_data'] = json.loads(order_dict['products_data'])
            return order_dict
        return None

def get_orders(status=None, limit=50):
    """الحصول على الطلبات للإدارة مع بيانات العميل."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = '''
            SELECT o.*, c.phone_number, c.name AS customer_name, c.address
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
        '''
        params = []
        if status:
            query += " WHERE o.order_status = ?"
            params.append(status)
        query += " ORDER BY o.created_at DESC LIMIT ?"
        params.append(int(limit))
        cursor.execute(query, params)
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item["products_data"] = json.loads(item.get("products_data") or "[]")
            except (TypeError, json.JSONDecodeError):
                item["products_data"] = []
            rows.append(item)
        conn.close()
        return rows

def get_customer_orders(phone_number, limit=20):
    """الحصول على طلبات عميل محدد برقم واتساب."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, c.phone_number, c.name AS customer_name, c.address
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE c.phone_number = ?
            ORDER BY o.created_at DESC LIMIT ?
        ''', (phone_number, int(limit)))
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            try:
                item["products_data"] = json.loads(item.get("products_data") or "[]")
            except (TypeError, json.JSONDecodeError):
                item["products_data"] = []
            rows.append(item)
        conn.close()
        return rows

def get_customers(limit=100):
    """الحصول على قائمة العملاء للإدارة."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers ORDER BY updated_at DESC LIMIT ?', (int(limit),))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

def search_customers(query, limit=20):
    """البحث عن عميل بالاسم أو الرقم أو العنوان."""
    pattern = f"%{query.strip()}%"
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM customers
            WHERE phone_number LIKE ? OR name LIKE ? OR address LIKE ?
            ORDER BY updated_at DESC LIMIT ?
        ''', (pattern, pattern, pattern, int(limit)))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

def update_order_payment_proof(order_number, proof_url):
    """حفظ صورة أو معرف إشعار التحويل للطلب."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders
            SET payment_proof_url = ?, order_status = 'بانتظار مراجعة الدفع', updated_at = CURRENT_TIMESTAMP
            WHERE order_number = ?
        ''', (proof_url, order_number))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

def update_order_status(order_number, new_status):
    """تحديث حالة الطلب"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders 
            SET order_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_number = ?
        ''', (new_status, order_number))
        
        conn.commit()
        conn.close()

def add_product(name, price, description="", image_id="", quantity=0, keywords=""):
    """إضافة منتج جديد"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO products (name, price, description, image_id, quantity, keywords)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, price, description, image_id, quantity, keywords))
            conn.commit()
            product_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            product_id = None
        
        conn.close()
        return product_id

def get_product(product_id):
    """الحصول على بيانات المنتج"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        return dict(product) if product else None

def get_all_products():
    """الحصول على جميع المنتجات"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products WHERE available = 1')
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return products

def log_action(log_type, phone_number, action, details=""):
    """تسجيل الإجراءات"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO logs (log_type, phone_number, action, details)
            VALUES (?, ?, ?, ?)
        ''', (log_type, phone_number, action, details))
        
        conn.commit()
        conn.close()

def load_qa():
    """تحميل جميع الأسئلة والأجوبة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT question, answer FROM qa')
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}

def save_qa(keyword, answer):
    """حفظ سؤال وجواب"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO qa (question, answer) VALUES (?, ?)', (keyword, answer))
        except sqlite3.IntegrityError:
            cursor.execute('UPDATE qa SET answer=? WHERE question=?', (answer, keyword))
        conn.commit()
        conn.close()

def delete_qa(keyword):
    """حذف سؤال"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM qa WHERE question=?', (keyword,))
        conn.commit()
        conn.close()

def get_statistics():
    """الحصول على الإحصائيات"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # إجمالي المبيعات
        cursor.execute('SELECT SUM(total_price) as total_sales FROM orders WHERE order_status != "ملغي"')
        total_sales = cursor.fetchone()['total_sales'] or 0
        
        # عدد الطلبات
        cursor.execute('SELECT COUNT(*) as total_orders FROM orders')
        total_orders = cursor.fetchone()['total_orders']
        
        # عدد العملاء
        cursor.execute('SELECT COUNT(*) as total_customers FROM customers')
        total_customers = cursor.fetchone()['total_customers']
        
        # أكثر المنتجات مبيعاً
        cursor.execute('''
            SELECT p.name, SUM(json_extract(o.products_data, '$[*].quantity')) as total_sold
            FROM orders o
            JOIN products p
            WHERE o.order_status != 'ملغي'
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT 5
        ''')
        top_products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'total_customers': total_customers,
            'top_products': top_products
        }

# تهيئة قاعدة البيانات عند استيراد الملف
if __name__ != "__main__":
    init_db()
