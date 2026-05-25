# TriPro Backend - FastAPI server + SQLite
# Admin panel va Telegram bot o'rtasida API bog'lanish
# Barcha ma'lumotlar: akfa_orders va profilaktika jadvallari

import asyncio
import os
import random
import sqlite3
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
LOCAL_DB = str(BASE_DIR / 'tripro.db')

# ─── FASTAPI ───
app = FastAPI(title='TriPro API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ─── SQLITE JADVALLAR ───
def init_db():
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

# ─── 5 XONALI ID GENERATOR ───
def _generate_order_id():
    conn = sqlite3.connect(LOCAL_DB)
    existing = conn.execute('SELECT order_id FROM akfa_orders WHERE order_id IS NOT NULL').fetchall()
    ids = {r[0] for r in existing}
    conn.close()
    for _ in range(100):
        oid = str(random.randint(10000, 99999))
        if oid not in ids:
            return oid
    raise Exception('Unikal ID topilmadi')

# ─── AKFA BUYURTMALARI ───
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
    return dict(row) if row else None

def get_all_akfa_orders():
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM akfa_orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_akfa_status(order_id, new_status):
    valid = ['pending', 'material_delivered', 'assembling', 'cutting', 'ready']
    if new_status not in valid:
        return None
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute('UPDATE akfa_orders SET status = ? WHERE order_id = ?', (new_status, order_id))
    conn.commit()
    row = conn.execute('SELECT * FROM akfa_orders WHERE order_id = ?', (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ─── PROFILAKTIKA ───
def save_profilaktika(telegram_id, name, surname, phone, location, time_slot):
    conn = sqlite3.connect(LOCAL_DB)
    conn.execute(
        'INSERT INTO profilaktika (telegram_id, name, surname, phone, location, time_slot) VALUES (?, ?, ?, ?, ?, ?)',
        (telegram_id, name, surname, phone, location, time_slot)
    )
    conn.commit()
    conn.close()

def get_all_profilaktika():
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM profilaktika ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_profilaktika_status(pk_id, new_status):
    valid = ['pending', 'accepted', 'completed']
    if new_status not in valid:
        return None
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    conn.execute('UPDATE profilaktika SET status = ? WHERE id = ?', (new_status, pk_id))
    conn.commit()
    row = conn.execute('SELECT * FROM profilaktika WHERE id = ?', (pk_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ─── BIRLASHGAN RO'YXAT ───
def get_combined_orders():
    result = []
    for o in get_all_akfa_orders():
        result.append({
            'id': f'akfa_{o["id"]}',
            'pk': o['id'],
            'type': 'akfa',
            'order_id': o['order_id'] or '',
            'client': f"{o['name'] or ''} {o['surname'] or ''}".strip() or str(o['telegram_id']),
            'phone': o['phone'] or '',
            'info': f"Material: {o['material']}, Oyna: {o['glass_layer']}, Rang: {o['profile_color']}, O'lcham: {o['dimensions']}, Soni: {o['quantity']}",
            'status': o['status'],
            'created_at': o['created_at'],
        })
    for p in get_all_profilaktika():
        result.append({
            'id': f'prof_{p["id"]}',
            'pk': p['id'],
            'type': 'profilaktika',
            'order_id': '',
            'client': f"{p['name'] or ''} {p['surname'] or ''}".strip() or str(p['telegram_id']),
            'phone': p['phone'] or '',
            'info': f"Manzil: {p['location']}, Vaqt: {p['time_slot']}",
            'status': p['status'],
            'created_at': p['created_at'],
        })
    result.sort(key=lambda x: x['created_at'], reverse=True)
    return result

# ─── API ENDPOINTLAR ───
@app.get('/')
@app.get('/admin')
def serve_admin():
    return FileResponse(str(BASE_DIR / 'admin.html'))

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'TriPro API'}

@app.get('/api/orders')
def list_orders():
    return JSONResponse(get_combined_orders())

@app.post('/api/orders/akfa/{order_id}/status')
def change_akfa_status(order_id: str, body: dict):
    status = body.get('status', '')
    order = update_akfa_status(order_id, status)
    if not order:
        raise HTTPException(404, 'Buyurtma topilmadi')
    return JSONResponse(order)

@app.post('/api/orders/profilaktika/{pk_id}/status')
async def change_profilaktika_status(pk_id: int, body: dict):
    status = body.get('status', '')
    order = update_profilaktika_status(pk_id, status)
    if not order:
        raise HTTPException(404, 'Profilaktika topilmadi')

    try:
        from bot import bot
        if status == 'accepted':
            text = (
                '✅ Profilaktika arizangiz qabul qilindi!\n\n'
                f'📍 Manzil: {order["location"]}\n'
                f'⏰ Vaqt: {order["time_slot"]}\n\n'
                'Mutaxassisimiz belgilangan vaqtda sizga yetib boradi.'
            )
        elif status == 'completed':
            text = (
                '🏁 Profilaktika xizmati yakunlandi!\n\n'
                'Sizning deraza va romlaringizga profilaktika xizmati ko\'rsatildi. '
                'Keyingi profilaktika bir yildan so\'ng amalga oshiriladi.\n\n'
                'TriPro-ni tanlaganingiz uchun rahmat!'
            )
        else:
            text = None
        if text and order.get('telegram_id'):
            await bot.send_message(order['telegram_id'], text)
    except Exception as e:
        logger.warning(f"Profilaktika xabari yuborilmadi: {e}")

    return JSONResponse(order)

@app.post('/api/orders/profilaktika/{pk_id}/notify')
async def notify_profilaktika(pk_id: int):
    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute('SELECT * FROM profilaktika WHERE id = ?', (pk_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, 'Topilmadi')
    order = dict(row)
    try:
        from bot import bot
        text = (
            '📬 Profilaktika xizmati bo\'yicha yangi habar:\n\n'
            f'📍 Manzil: {order["location"]}\n'
            f'⏰ Vaqt: {order["time_slot"]}\n'
            f'📊 Holat: {order["status"]}'
        )
        if order.get('telegram_id'):
            await bot.send_message(order['telegram_id'], text)
        return {'status': 'sent'}
    except Exception as e:
        raise HTTPException(500, f'Xabar yuborilmadi: {e}')

# ─── BOTNI ISHGA TUSHIRISH ───
@app.on_event('startup')
async def startup():
    init_db()
    from bot import bot_main
    asyncio.create_task(bot_main(start_web_server=False))
    logger.info('Bot ishga tushirildi')

if __name__ == '__main__':
    import uvicorn
    PORT = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=PORT)
