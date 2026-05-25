# TriPro Database - SQLite (akfa buyurtmalari va profilaktika) + Supabase (admin panel)

import os
import random
import sqlite3
import httpx

LOCAL_DB = 'tripro.db'

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://ulsphhncfwjlchmbbwvm.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsc3BoaG5jZndqbGNobWJid3ZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTI3MjQwOSwiZXhwIjoyMDk0ODQ4NDA5fQ.IT1vWElu5kgyxs4AtWqT1rPq3jbRZ_0v5SbrmjjMWFc')
BASE = f'{SUPABASE_URL}/rest/v1'

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
}

def _get(path, params=None):
    with httpx.Client() as c:
        r = c.get(f'{BASE}/{path}', headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()

def _post(path, data, params=None):
    with httpx.Client() as c:
        r = c.post(f'{BASE}/{path}', headers=HEADERS, json=data, params=params)
        r.raise_for_status()
        return r.json()

def _patch(path, data, params=None):
    with httpx.Client() as c:
        r = c.patch(f'{BASE}/{path}', headers=HEADERS, json=data, params=params)
        r.raise_for_status()
        return r.json()

def init_db():
    # AKFA buyurtmalari jadvali
    conn = sqlite3.connect(LOCAL_DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS akfa_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE,
        telegram_id INTEGER,
        name TEXT,
        surname TEXT,
        phone TEXT,
        material TEXT,
        glass_layer TEXT,
        profile_color TEXT,
        dimensions TEXT,
        quantity INTEGER DEFAULT 1,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Profilaktika xizmati jadvali
    conn.execute('''CREATE TABLE IF NOT EXISTS profilaktika (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        name TEXT,
        surname TEXT,
        phone TEXT,
        location TEXT,
        time_slot TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# ─── SQLITE: AKFA BUYURTMALARI ───

def _generate_order_id():
    conn = sqlite3.connect(LOCAL_DB)
    existing = conn.execute('SELECT order_id FROM akfa_orders WHERE order_id IS NOT NULL').fetchall()
    ids = {r[0] for r in existing}
    conn.close()
    for _ in range(100):
        oid = str(random.randint(10000, 99999))
        if oid not in ids:
            return oid
    raise Exception('No unique order ID available')

def save_akfa_order(telegram_id, name, surname, phone, material, glass_layer, profile_color, dimensions, quantity=1):
    order_id = _generate_order_id()
    conn = sqlite3.connect(LOCAL_DB)
    conn.execute(
        'INSERT INTO akfa_orders (order_id, telegram_id, name, surname, phone, material, glass_layer, profile_color, dimensions, quantity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (order_id, telegram_id, name, surname, phone, material, glass_layer, profile_color, dimensions, quantity)
    )
    conn.commit()
    conn.close()
    return order_id

def get_akfa_order(order_id):
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM akfa_orders WHERE order_id = ?', (order_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# ─── SQLITE: PROFILAKTIKA ───

def save_profilaktika(telegram_id, name, surname, phone, location, time_slot):
    conn = sqlite3.connect(LOCAL_DB)
    conn.execute(
        'INSERT INTO profilaktika (telegram_id, name, surname, phone, location, time_slot) VALUES (?, ?, ?, ?, ?, ?)',
        (telegram_id, name, surname, phone, location, time_slot)
    )
    conn.commit()
    conn.close()

# ─── SUPABASE (admin panel uchun) ───

def _generate_supabase_order_id():
    existing = _get('orders', params={'select': 'order_id'})
    ids = {r['order_id'] for r in existing if r['order_id']}
    for _ in range(100):
        oid = str(random.randint(1000, 9999))
        if oid not in ids:
            return oid
    raise Exception('No unique order ID available')

def create_order(telegram_id, material_type, glass_type, profile_color, dimensions, phone,
                 glass_pattern=None, glass_color=None, quantity=1):
    data = {
        'telegram_id': telegram_id,
        'material_type': material_type,
        'glass_type': glass_type,
        'profile_color': profile_color,
        'dimensions': dimensions,
        'phone': phone,
        'glass_pattern': glass_pattern,
        'glass_color': glass_color,
        'quantity': quantity,
    }
    rows = _post('orders', data)
    return rows[0]['id'] if rows else None

def get_order(order_id_or_pk):
    if order_id_or_pk is None:
        return None
    s = str(order_id_or_pk)
    if s.isdigit() and len(s) == 4:
        rows = _get('orders', params={'order_id': f'eq.{s}', 'limit': '1'})
    else:
        rows = _get('orders', params={'id': f'eq.{s}', 'limit': '1'})
        if not rows:
            rows = _get('orders', params={'order_id': f'eq.{s}', 'limit': '1'})
    return rows[0] if rows else None

def get_all_orders():
    return _get('orders', params={'order': 'created_at.desc'})

def get_pending_orders():
    return _get('orders', params={'status': 'eq.pending', 'order': 'created_at.desc'})

def get_orders_for_chat(telegram_id):
    return _get('orders', params={'telegram_id': f'eq.{telegram_id}', 'order': 'created_at.desc'})

def confirm_order(order_id):
    if order_id is None:
        return None
    s = str(order_id)
    if s.isdigit() and len(s) == 4:
        rows = _get('orders', params={'order_id': f'eq.{s}', 'limit': '1'})
    else:
        rows = _get('orders', params={'id': f'eq.{s}', 'limit': '1'})
        if not rows:
            rows = _get('orders', params={'order_id': f'eq.{s}', 'limit': '1'})
    if not rows:
        return None
    existing = rows[0]
    if existing['status'] != 'pending':
        return existing
    new_id = existing.get('order_id') or _generate_supabase_order_id()
    rows = _patch('orders', {'status': 'material_delivered', 'order_id': new_id},
                  params={'id': f'eq.{existing["id"]}', 'select': '*'})
    return rows[0] if rows else None

def update_status(order_id, new_status):
    valid = ['pending', 'confirmed', 'material_delivered', 'in_progress', 'ready', 'delivered']
    if new_status not in valid:
        return None
    rows = _patch('orders', {'status': new_status},
                  params={'order_id': f'eq.{order_id}', 'select': '*'})
    return rows[0] if rows else None

def get_unnotified_confirmations():
    return _get('orders', params={
        'status': 'eq.material_delivered',
        'notified': 'eq.0',
        'order_id': 'not.is.null',
        'order': 'created_at.desc',
    })

def mark_notified(order_id):
    _patch('orders', {'notified': 1}, params={'order_id': f'eq.{order_id}'})

def get_unnotified_deliveries():
    return _get('orders', params={
        'status': 'eq.delivered',
        'delivery_notified': 'eq.0',
        'order_id': 'not.is.null',
        'order': 'created_at.desc',
    })

def mark_delivery_notified(order_id):
    _patch('orders', {'delivery_notified': 1}, params={'order_id': f'eq.{order_id}'})
