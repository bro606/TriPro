import aiosqlite
import datetime
import os

from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'tripro.db'))

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Akfa buyurtmalari jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS akfa_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id TEXT UNIQUE,
                name TEXT,
                surname TEXT,
                phone TEXT,
                info TEXT,
                dimensions TEXT,
                quantity INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Profilaktika va usta chaqirish jadvali
        await db.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                phone TEXT,
                problem TEXT,
                status TEXT DEFAULT 'pending',
                type TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Foydalanuvchilar (reklama yuborish uchun)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

# --- AKFA ORDERS QUERIES ---

async def save_akfa_order(user_id, name, surname, phone, info, dimensions, quantity):
    oid = datetime.datetime.now().strftime('%H%M%S')[-5:]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO akfa_orders (user_id, order_id, name, surname, phone, info, dimensions, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, oid, name, surname, phone, info, dimensions, quantity))
        await db.commit()
    return oid

async def get_akfa_order(order_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM akfa_orders WHERE order_id = ?', (order_id,)) as cursor:
            return await cursor.fetchone()

async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM akfa_orders ORDER BY created_at DESC') as cursor:
            return await cursor.fetchall()

async def update_order_status(order_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        completed_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'ready' else None
        if completed_at:
            await db.execute('UPDATE akfa_orders SET status = ?, completed_at = ? WHERE order_id = ?', 
                           (status, completed_at, order_id))
        else:
            await db.execute('UPDATE akfa_orders SET status = ? WHERE order_id = ?', (status, order_id))
        await db.commit()

# --- MAINTENANCE QUERIES ---

async def save_maintenance_request(user_id, name, phone, problem, request_type='manual'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO maintenance_requests (user_id, name, phone, problem, type)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, phone, problem, request_type))
        await db.commit()

async def get_all_maintenance():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM maintenance_requests ORDER BY created_at DESC') as cursor:
            return await cursor.fetchall()

async def update_maintenance_status(request_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE maintenance_requests SET status = ? WHERE id = ?', (status, request_id))
        await db.commit()

# --- AUTO CHECK 6 MONTHS ---

async def get_orders_for_maintenance():
    """Builds a list of users who completed orders exactly 180 days ago."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        target_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
        # We search orders that were 'ready' 180 days ago
        async with db.execute("SELECT * FROM akfa_orders WHERE status = 'ready' AND completed_at LIKE ?", (f'{target_date}%',)) as cursor:
            return await cursor.fetchall()

# --- SYSTEM ---
async def save_user(u_id, username, f_name, l_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                       (u_id, username, f_name, l_name))
        await db.commit()
