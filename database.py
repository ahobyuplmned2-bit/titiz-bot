"""
نظام إدارة قاعدة البيانات للمشروع
يدعم SQLite للتطوير و PostgreSQL للإنتاج
"""

import sqlite3
import os
import json
import time
import shutil
from datetime import datetime
from threading import Lock

# قفل للتعامل الآمن مع قاعدة البيانات
db_lock = Lock()

# اختيار نوع قاعدة البيانات. عند ضبط DATABASE_PATH على قرص دائم في Render
# تنتقل كل بيانات البوت (المحادثات والطلبات والسلة والتذكيرات) إلى المسار نفسه.
USE_SQLITE = True
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "titiz_bot.db")


def _resolve_db_path():
    """اختيار مسار SQLite القابل للاستمرار وترحيل الملف المحلي في أول تشغيل."""
    configured_path = (os.environ.get("DATABASE_PATH") or "").strip()
    database_path = os.path.abspath(os.path.expanduser(configured_path or DEFAULT_DB_PATH))
    database_dir = os.path.dirname(database_path)
    if database_dir:
        os.makedirs(database_dir, exist_ok=True)

    # عند تفعيل القرص الدائم لأول مرة، نحافظ على البيانات المحلية المتاحة
    # بنسخها إلى المسار الجديد بدلاً من البدء بقاعدة فارغة.
    if (
        database_path != DEFAULT_DB_PATH
        and not os.path.exists(database_path)
        and os.path.isfile(DEFAULT_DB_PATH)
    ):
        try:
            shutil.copy2(DEFAULT_DB_PATH, database_path)
            print(f"[قاعدة البيانات] تم ترحيل البيانات إلى المسار الدائم: {database_path}")
        except OSError as exc:
            print(f"[قاعدة البيانات] تعذر ترحيل النسخة المحلية: {exc}")
    return database_path


DB_PATH = _resolve_db_path()

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
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN image_urls TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN variants TEXT')
        except sqlite3.OperationalError:
            pass
        
        # جدول السلة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                variant_name TEXT,
                variant_price REAL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        try:
            cursor.execute('ALTER TABLE cart ADD COLUMN variant_name TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE cart ADD COLUMN variant_price REAL')
        except sqlite3.OperationalError:
            pass
        
        # جدول جلسات المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                session_data TEXT,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # سجل تواصل مستقل عن customers، حتى لا يُحفظ العميل في customers.json قبل إكمال بياناته.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                phone_number TEXT PRIMARY KEY,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # سجل دائم لمعرّفات رسائل واتساب لمنع إعادة معالجة webhook المكرر.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_webhook_messages (
                message_id TEXT PRIMARY KEY,
                received_at REAL NOT NULL
            )
        ''')

        # سجل موحد دائم لكل الرسائل الواردة والصادرة ونتائج الفهم.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                whatsapp_message_id TEXT,
                direction TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                message_type TEXT,
                body TEXT,
                normalized_body TEXT,
                caption TEXT,
                media_id TEXT,
                intent TEXT,
                intent_confidence REAL,
                product_id INTEGER,
                order_number TEXT,
                ai_model TEXT,
                ai_status TEXT,
                ai_result TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_events_phone_time "
            "ON message_events(phone_number, created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_message_events_intent "
            "ON message_events(intent, created_at)"
        )

        # عداد ثابت خاص بإشعارات الإدارة، منفصل عن سجل الرسائل كي لا تتخطى
        # الأرقام بسبب الأزرار أو الأحداث التقنية أو الردود الصادرة من البوت.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS owner_notification_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_event_id INTEGER UNIQUE,
                phone_number TEXT NOT NULL,
                sequence_number INTEGER UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ردود الإدارة المؤجلة حتى يراسل العميل البوت لأول مرة.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # تذكيرات متابعة استفسارات المنتجات، محفوظة لاستمرارها بعد إعادة التشغيل.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                product_name TEXT,
                context_text TEXT,
                due_at REAL NOT NULL,
                sent_at REAL,
                followup_kind TEXT DEFAULT 'satisfaction',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cursor.execute('ALTER TABLE customer_followups ADD COLUMN context_text TEXT')
        except sqlite3.OperationalError:
            pass
        
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
            "customer_followups": {
                "followup_kind": "TEXT DEFAULT 'satisfaction'",
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


def claim_processed_webhook_message(message_id, received_at=None):
    """تسجيل رسالة واتساب مرة واحدة فقط عبر INSERT ذري آمن."""
    if not message_id:
        return True
    received_at = float(received_at if received_at is not None else time.time())
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM processed_webhook_messages WHERE received_at < ?",
            (received_at - 86400,),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO processed_webhook_messages (message_id, received_at) VALUES (?, ?)",
            (str(message_id), received_at),
        )
        claimed = cursor.rowcount == 1
        conn.commit()
        conn.close()
        return claimed

def record_message_event(
    *,
    whatsapp_message_id=None,
    direction="inbound",
    phone_number="",
    message_type="text",
    body="",
    normalized_body="",
    caption="",
    media_id="",
    intent=None,
    intent_confidence=None,
    product_id=None,
    order_number=None,
    ai_model=None,
    ai_status=None,
    ai_result=None,
    response_text=None,
):
    """حفظ رسالة أو رد مع بيانات الفهم دون تعطيل مسار واتساب إذا تعذر التسجيل."""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                """
                INSERT INTO message_events (
                    whatsapp_message_id, direction, phone_number, message_type,
                    body, normalized_body, caption, media_id, intent,
                    intent_confidence, product_id, order_number, ai_model,
                    ai_status, ai_result, response_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    whatsapp_message_id,
                    direction,
                    str(phone_number or ""),
                    message_type,
                    body,
                    normalized_body,
                    caption,
                    media_id,
                    intent,
                    intent_confidence,
                    product_id,
                    order_number,
                    ai_model,
                    ai_status,
                    ai_result,
                    response_text,
                ),
            )
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return event_id
    except Exception as exc:
        print(f"[سجل الرسائل] تعذر حفظ الحدث: {exc}")
        return None


def reserve_owner_notification_sequence(phone_number="", message_event_id=None):
    """حجز رقم متسلسل واحد لإشعار إدارة رسالة عميل واردة."""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            if message_event_id is not None:
                existing = conn.execute(
                    "SELECT sequence_number FROM owner_notification_sequences WHERE message_event_id = ?",
                    (message_event_id,),
                ).fetchone()
                if existing:
                    conn.close()
                    return int(existing[0])

            current = conn.execute(
                "SELECT COALESCE(MAX(sequence_number), 0) FROM owner_notification_sequences"
            ).fetchone()
            next_sequence = int(current[0] or 0) + 1
            conn.execute(
                "INSERT INTO owner_notification_sequences (message_event_id, phone_number, sequence_number) "
                "VALUES (?, ?, ?)",
                (message_event_id, str(phone_number or ""), next_sequence),
            )
            conn.commit()
            conn.close()
            return next_sequence
    except Exception as exc:
        print(f"[إشعارات الإدارة] تعذر حجز رقم الرسالة: {exc}")
        return None


def update_message_event(event_id, **fields):
    """تحديث نتيجة التصنيف أو ربط الرسالة بمنتج أو طلب بعد المعالجة."""
    allowed = {
        "intent", "intent_confidence", "product_id", "order_number",
        "ai_model", "ai_status", "ai_result", "response_text",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not event_id or not updates:
        return False
    try:
        assignments = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [event_id]
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute(
                f"UPDATE message_events SET {assignments} WHERE id = ?",
                values,
            )
            conn.commit()
            changed = cursor.rowcount > 0
            conn.close()
            return changed
    except Exception as exc:
        print(f"[سجل الرسائل] تعذر تحديث الحدث: {exc}")
        return False


def get_message_events(limit=100, phone_number=None, intent=None):
    """قراءة آخر الرسائل للوحة الإدارة أو المراجعة."""
    limit = max(1, min(int(limit or 100), 500))
    clauses = []
    params = []
    if phone_number:
        clauses.append("phone_number = ?")
        params.append(str(phone_number))
    if intent:
        clauses.append("intent = ?")
        params.append(str(intent))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM message_events {where} ORDER BY id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        conn.close()
    return [dict(row) for row in rows]


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

def _positive_price(value):
    """تحويل السعر إلى رقم موجب؛ السعر الفارغ أو الصفري غير صالح."""
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def add_to_cart(phone_number, product_id, quantity=1, variant_name="", variant_price=None):
    """إضافة منتج إلى السلة"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        selected_price = _positive_price(variant_price) if variant_price is not None else None
        if variant_price is not None and selected_price is None:
            conn.close()
            return False
        if variant_price is None:
            product_row = cursor.execute(
                "SELECT price FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if not product_row or _positive_price(product_row[0]) is None:
                conn.close()
                return False
        
        cursor.execute('''
            SELECT id, quantity FROM cart
            WHERE phone_number = ? AND product_id = ? AND COALESCE(variant_name, '') = ?
        ''', (phone_number, product_id, variant_name or ""))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE cart SET quantity = quantity + ? 
                WHERE phone_number = ? AND product_id = ? AND COALESCE(variant_name, '') = ?
            ''', (quantity, phone_number, product_id, variant_name or ""))
        else:
            cursor.execute('''
                INSERT INTO cart (phone_number, product_id, quantity, variant_name, variant_price)
                VALUES (?, ?, ?, ?, ?)
            ''', (phone_number, product_id, quantity, variant_name or "", selected_price))
        
        conn.commit()
        conn.close()
        return True

def get_cart(phone_number):
    """الحصول على سلة العميل"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.product_id, c.quantity, p.name,
                   COALESCE(c.variant_price, p.price) AS price,
                   COALESCE(c.variant_name, '') AS variant_name,
                   p.image_id
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

def record_contact(phone_number):
    """تسجيل أن الرقم راسل البوت، دون اعتباره عميلاً مكتمل البيانات."""
    if not phone_number:
        return
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO contacts (phone_number, first_seen_at, last_seen_at)
            VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET
                last_seen_at = CURRENT_TIMESTAMP
        ''', (phone_number,))
        conn.commit()
        conn.close()

def has_contact(phone_number):
    """التحقق من أن الرقم سبق أن أرسل رسالة إلى البوت."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            'SELECT 1 FROM contacts WHERE phone_number = ? LIMIT 1',
            (phone_number,),
        ).fetchone()
        conn.close()
        return row is not None

def queue_pending_reply(phone_number, message):
    """حفظ رد الإدارة حتى يراسل العميل البوت."""
    if not phone_number or not message:
        return False
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO pending_replies (phone_number, message) VALUES (?, ?)',
            (phone_number, message),
        )
        conn.commit()
        conn.close()
        return True

def get_pending_replies(phone_number, limit=20):
    """الحصول على الردود المؤجلة غير المرسلة للعميل."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('''
            SELECT id, phone_number, message, created_at
            FROM pending_replies
            WHERE phone_number = ? AND sent_at IS NULL
            ORDER BY id ASC LIMIT ?
        ''', (phone_number, int(limit))).fetchall()
        conn.close()
        return [dict(row) for row in rows]

def mark_pending_reply_sent(reply_id):
    """تمييز الرد المؤجل كمرسل بعد نجاح واتساب."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE pending_replies SET sent_at = CURRENT_TIMESTAMP WHERE id = ? AND sent_at IS NULL',
            (int(reply_id),),
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

def schedule_customer_followup(
    phone_number,
    product_name="",
    delay_seconds=86400,
    followup_kind="satisfaction",
    context_text="",
):
    """جدولة متابعة واحدة للعميل، مع استبدال أي متابعة سابقة."""
    due_at = datetime.utcnow().timestamp() + max(int(delay_seconds), 60)
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            INSERT INTO customer_followups
                (phone_number, product_name, context_text, due_at, sent_at, followup_kind, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone_number) DO UPDATE SET
                product_name = excluded.product_name,
                context_text = excluded.context_text,
                due_at = excluded.due_at,
                sent_at = NULL,
                followup_kind = excluded.followup_kind,
                updated_at = CURRENT_TIMESTAMP
        ''', (
            phone_number,
            product_name or "",
            context_text or "",
            due_at,
            followup_kind or "satisfaction",
        ))
        conn.commit()
        conn.close()

def cancel_customer_followup(phone_number):
    """إلغاء تذكير العميل عند عودته للمحادثة أو تفاعله مع التذكير."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM customer_followups WHERE phone_number = ?', (phone_number,))
        conn.commit()
        conn.close()

def get_due_customer_followups(limit=50):
    """إرجاع التذكيرات المستحقة التي لم تُرسل بعد."""
    now = datetime.utcnow().timestamp()
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute('''
            SELECT phone_number, product_name, context_text, due_at, followup_kind
            FROM customer_followups
            WHERE sent_at IS NULL AND due_at <= ?
            ORDER BY due_at ASC
            LIMIT ?
        ''', (now, int(limit))).fetchall()
        conn.close()
        return [dict(row) for row in rows]

def get_customer_followup(phone_number):
    """الحصول على آخر متابعة للعميل، بما فيها المتابعة التي أُرسلت."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute('''
            SELECT phone_number, product_name, context_text, due_at, sent_at, followup_kind
            FROM customer_followups
            WHERE phone_number = ?
        ''', (phone_number,)).fetchone()
        conn.close()
        return dict(row) if row else None

def mark_customer_followup_sent(phone_number, due_at):
    """حجز التذكير للإرسال مرة واحدة فقط حتى لا يتكرر."""
    sent_at = datetime.utcnow().timestamp()
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE customer_followups
            SET sent_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE phone_number = ? AND due_at = ? AND sent_at IS NULL
        ''', (sent_at, phone_number, due_at))
        claimed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return claimed

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
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

def add_product(name, price, description="", image_id="", quantity=0, keywords="", image_urls="", variants=""):
    """إضافة منتج جديد"""
    validated_price = _positive_price(price)
    if validated_price is None:
        return None
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO products (name, price, description, image_id, quantity, keywords, image_urls, variants)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, validated_price, description, image_id, quantity, keywords, image_urls, variants))
            conn.commit()
            product_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            product_id = None
        
        conn.close()
        return product_id


def update_product_metadata(name, price, description="", image_id="", keywords="", image_urls="", variants=""):
    """تحديث بيانات المنتج من products.json دون تغيير الكمية أو حالة التوفر."""
    validated_price = _positive_price(price)
    if validated_price is None:
        return False
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products
            SET price = ?, description = ?, image_id = ?, keywords = ?, image_urls = ?, variants = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
        ''', (validated_price, description, image_id, keywords, image_urls, variants, name))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated


def update_product_fields(product_id, name=None, price=None, description=None):
    """تعديل الحقول الإدارية الأساسية مع الحفاظ على الصور والكلمات والخيارات."""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current = cursor.execute(
            "SELECT name FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()
        if not current:
            conn.close()
            return None
        if name and cursor.execute(
            "SELECT id FROM products WHERE name = ? AND id != ?", (name, int(product_id))
        ).fetchone():
            conn.close()
            return "duplicate"

        assignments = []
        values = []
        if name is not None:
            assignments.append("name = ?")
            values.append(name)
        if price is not None:
            validated_price = _positive_price(price)
            if validated_price is None:
                conn.close()
                return "invalid_price"
            assignments.append("price = ?")
            values.append(validated_price)
        if description is not None:
            assignments.append("description = ?")
            values.append(description)
        if not assignments:
            conn.close()
            return dict(id=int(product_id), name=current[0])
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        values.append(int(product_id))
        cursor.execute(
            f"UPDATE products SET {', '.join(assignments)} WHERE id = ?", values
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()
        columns = [column[1] for column in cursor.execute("PRAGMA table_info(products)").fetchall()]
        conn.close()
        return dict(zip(columns, updated)) if updated else None

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
        
        cursor.execute('SELECT * FROM products WHERE available = 1 ORDER BY id ASC')
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
