import datetime
import os
import time
import aiohttp

FIREBASE_URL = os.getenv('FIREBASE_DATABASE_URL', 'https://tripro-d6f16-default-rtdb.firebaseio.com').rstrip('/')

async def init_db():
    # Firebase Realtime Database is schema-less; tables are automatically created on insertion.
    pass

# --- AKFA ORDERS QUERIES ---

async def save_akfa_order(user_id, name, surname, phone, info, dimensions, quantity):
    oid = datetime.datetime.now().strftime('%H%M%S')[-5:]
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    order_data = {
        "user_id": user_id,
        "order_id": oid,
        "name": name,
        "surname": surname,
        "phone": phone,
        "info": info,
        "dimensions": dimensions,
        "quantity": quantity,
        "status": "pending",
        "created_at": created_at,
        "completed_at": None
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{FIREBASE_URL}/akfa_orders/{oid}.json", json=order_data) as resp:
            await resp.json()
    return oid

async def get_akfa_order(order_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FIREBASE_URL}/akfa_orders/{order_id}.json") as resp:
            data = await resp.json()
            return data

async def get_all_orders():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FIREBASE_URL}/akfa_orders.json") as resp:
            data = await resp.json()
            if not data:
                return []
            orders = list(data.values())
            # Sort by created_at descending
            orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return orders

async def update_order_status(order_id, status):
    completed_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'ready' else None
    updates = {
        "status": status
    }
    if completed_at:
        updates["completed_at"] = completed_at
    async with aiohttp.ClientSession() as session:
        async with session.patch(f"{FIREBASE_URL}/akfa_orders/{order_id}.json", json=updates) as resp:
            await resp.json()

# --- MAINTENANCE QUERIES ---

async def save_maintenance_request(user_id, name, phone, problem, request_type='manual'):
    req_id = int(time.time())
    created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    req_data = {
        "id": req_id,
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "problem": problem,
        "status": "pending",
        "type": request_type,
        "created_at": created_at
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{FIREBASE_URL}/maintenance_requests/{req_id}.json", json=req_data) as resp:
            await resp.json()
    return req_id

async def get_all_maintenance():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FIREBASE_URL}/maintenance_requests.json") as resp:
            data = await resp.json()
            if not data:
                return []
            reqs = list(data.values())
            reqs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return reqs

async def update_maintenance_status(request_id, status):
    async with aiohttp.ClientSession() as session:
        async with session.patch(f"{FIREBASE_URL}/maintenance_requests/{request_id}.json", json={"status": status}) as resp:
            await resp.json()

async def get_maintenance_request(request_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FIREBASE_URL}/maintenance_requests/{request_id}.json") as resp:
            return await resp.json()

# --- AUTO CHECK 6 MONTHS ---

async def get_orders_for_maintenance():
    """Builds a list of users who completed orders exactly 180 days ago."""
    target_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FIREBASE_URL}/akfa_orders.json") as resp:
            data = await resp.json()
            if not data:
                return []
            matches = []
            for o in data.values():
                if o.get('status') == 'ready' and o.get('completed_at') and o.get('completed_at').startswith(target_date):
                    matches.append(o)
            return matches

# --- SYSTEM ---
async def save_user(u_id, username, f_name, l_name):
    user_data = {
        "user_id": u_id,
        "username": username,
        "first_name": f_name,
        "last_name": l_name,
        "joined_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{FIREBASE_URL}/users/{u_id}.json", json=user_data) as resp:
            await resp.json()
