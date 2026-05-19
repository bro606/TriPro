import sqlite3
import random
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'tripro.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            telegram_id INTEGER NOT NULL,
            material_type TEXT,
            glass_type TEXT,
            profile_color TEXT,
            dimensions TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            notified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    conn.close()

def _generate_order_id(conn):
    for _ in range(100):
        oid = str(random.randint(1000, 9999))
        if not conn.execute('SELECT 1 FROM orders WHERE order_id = ?', (oid,)).fetchone():
            return oid
    raise Exception('No unique order ID available')

def create_order(telegram_id, material_type, glass_type, profile_color, dimensions, phone):
    conn = get_conn()
    conn.execute('''
        INSERT INTO orders (telegram_id, material_type, glass_type, profile_color, dimensions, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, material_type, glass_type, profile_color, dimensions, phone))
    conn.commit()
    row_id = conn.execute('SELECT id FROM orders WHERE rowid = last_insert_rowid()').fetchone()[0]
    conn.close()
    return row_id

def get_order(order_id_or_pk):
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM orders WHERE order_id = ? OR id = ?', (str(order_id_or_pk), order_id_or_pk)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_orders():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_orders():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC', ('pending',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_orders_for_chat(telegram_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC', (telegram_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def confirm_order(order_id):
    conn = get_conn()
    row = conn.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,)).fetchone()
    if not row:
        conn.close()
        return None
    existing = dict(row)
    if existing['status'] != 'pending':
        conn.close()
        return existing
    if not existing['order_id']:
        new_id = _generate_order_id(conn)
        conn.execute(
            'UPDATE orders SET order_id = ?, status = ?, updated_at = datetime("now") WHERE id = ?',
            (new_id, 'confirmed', existing['id'])
        )
    else:
        conn.execute(
            'UPDATE orders SET status = ?, updated_at = datetime("now") WHERE id = ?',
            ('confirmed', existing['id'])
        )
    conn.commit()
    updated = conn.execute('SELECT * FROM orders WHERE id = ?', (existing['id'],)).fetchone()
    conn.close()
    return dict(updated)

def update_status(order_id, new_status):
    valid = ['pending', 'confirmed', 'material_delivered', 'in_progress', 'ready', 'delivered']
    if new_status not in valid:
        return None
    conn = get_conn()
    conn.execute(
        'UPDATE orders SET status = ?, updated_at = datetime("now") WHERE order_id = ?',
        (new_status, str(order_id))
    )
    conn.commit()
    row = conn.execute('SELECT * FROM orders WHERE order_id = ?', (str(order_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_unnotified_confirmations():
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM orders WHERE status = ? AND notified = 0 AND order_id IS NOT NULL',
        ('confirmed',)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notified(order_id):
    conn = get_conn()
    conn.execute('UPDATE orders SET notified = 1 WHERE order_id = ?', (str(order_id),))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Database initialized.')
