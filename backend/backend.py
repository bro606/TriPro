# TriPro FastAPI Backend - professional CRM mantiqi
import asyncio, os, logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from aiogram import types

# Bot va Baza importlari
try:
    from .bot import bot, dp
    from .database import (
        init_db, save_akfa_order, get_akfa_order, get_all_orders, update_order_status,
        get_all_maintenance, update_maintenance_status, get_orders_for_maintenance
    )
except ImportError:
    from bot import bot, dp
    from database import (
        init_db, save_akfa_order, get_akfa_order, get_all_orders, update_order_status,
        get_all_maintenance, update_maintenance_status, get_orders_for_maintenance
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('backend')

PORT = int(os.getenv('PORT', '10000'))
PUBLIC_URL = os.getenv('PUBLIC_URL', 'https://tripro.onrender.com').strip()
if PUBLIC_URL.endswith('/'): PUBLIC_URL = PUBLIC_URL[:-1]

# ═══════════════════════════════════════════════
# AUTO MAINTENANCE TASK (180 KUNLIK TEKSHIRUV)
# ═══════════════════════════════════════════════

async def maintenance_reminder_task():
    """Har 24 soatda ishlaydi va 6 oylik mijozlarni qutlaydi"""
    while True:
        try:
            logger.info("===> 6-oylik profilaktika tekshiruvi boshlandi...")
            orders = await get_orders_for_maintenance()
            for o in orders:
                try:
                    txt = (
                        "🏠 **Assalomu alaykum!**\n\nTriPro ustaxonasida eshik va deraza romlarini buyurtma qilganingizga naqd 6 oy bo'libdi!\n\n"
                        "Biz sifatni nazorat qilish maqsadida profilaktika xizmatini taklif qilamiz. Agar nosozliklar bo'lsa, "
                        "ustalarimiz borib ko'rishadi va ish hajmidan kelib chiqib narx kelishiladi.\n\n"
                        "Xizmatdan foydalanish uchun quyidagi tugmani bosing:"
                    )
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="🛠 Usta chaqirish", callback_data="call_master")]
                    ])
                    await bot.send_message(chat_id=o['user_id'], text=txt, reply_markup=kb, parse_mode='Markdown')
                    logger.info(f"===> Reminder sent to {o['user_id']}")
                except Exception as ex:
                    logger.warning(f"Reminder error for user {o['user_id']}: {ex}")
            
            await asyncio.sleep(86400) # 24 soat kutiladi
        except Exception as e:
            logger.error(f"Maintenance task loop error: {e}")
            await asyncio.sleep(3600)

# ═══════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    # Webhook
    webhook_url = f"{PUBLIC_URL}/webhook/bot"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])
    logger.info(f"===> Webhook set: {webhook_url}")
    
    # Fon vazifasini ishga tushirish
    asyncio.create_task(maintenance_reminder_task())
    
    yield
    logger.info("Server shuts down.")

app = FastAPI(title='TriPro Professional API', lifespan=lifespan)

# ═══════════════════════════════════════════════
# WEBHOOK ENDPOINT
# ═══════════════════════════════════════════════

@app.post('/webhook/bot')
async def telegram_webhook(update: dict):
    try:
        telegram_update = types.Update.model_validate(update, context={"bot": bot})
        await dp.feed_update(bot=bot, update=telegram_update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook process error: {e}")
        return {"status": "error"}

@app.get('/', response_class=HTMLResponse)
async def health_and_admin():
    # Asosiy sahifada admin panelini ko'rsatamiz
    admin_path = os.path.join(os.path.dirname(__file__), '..', 'admin.html')
    if os.path.exists(admin_path):
        with open(admin_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "TriPro API is active. admin.html not found in root."

# ═══════════════════════════════════════════════
# ADMIN API ENDPOINTS
# ═══════════════════════════════════════════════

@app.get('/api/orders')
async def list_orders():
    orders = await get_all_orders()
    return [dict(o) for o in orders]

@app.get('/api/maintenance')
async def list_maintenance():
    reqs = await get_all_maintenance()
    return [dict(r) for r in reqs]

class StatusUpdate(BaseModel):
    status: str

@app.post('/api/orders/{order_id}/status')
async def set_order_status(order_id: str, body: StatusUpdate):
    await update_order_status(order_id, body.status)
    # Bildirishnoma yuborish
    o = await get_akfa_order(order_id)
    if o and body.status == 'ready':
        try:
            await bot.send_message(o['user_id'], f"🏁 **Buyurtmangiz (ID: {order_id}) tayyor va yetkazilmoqda!**\nXizmatimizdan foydalanganingiz uchun rahmat.", parse_mode='Markdown')
        except: pass
    return {"ok": True}

@app.post('/api/maintenance/{req_id}/status')
async def set_maintenance_status(req_id: int, body: StatusUpdate):
    await update_maintenance_status(req_id, body.status)
    return {"ok": True}

if __name__ == '__main__':
    uvicorn.run('backend:app', host='0.0.0.0', port=PORT, reload=True)
