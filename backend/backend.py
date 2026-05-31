# TriPro FastAPI Backend - admin panel uchun
import asyncio, os, json, threading
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from aiogram import types
from bot import bot, dp, BOT_TOKEN, get_akfa_order, get_all_akfa, update_akfa, get_all_prof, update_prof, get_combined_orders, init_db, logger

PORT = int(os.getenv('PORT', '10000'))

# init_db is now async, we'll call it in lifespan or manually

PUBLIC_URL = os.getenv('PUBLIC_URL', 'https://tripro.onrender.com').strip()
if PUBLIC_URL.endswith('/'): PUBLIC_URL = PUBLIC_URL[:-1]

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # MA'LUMOTLAR BAZASINI ISHGA TUSHIRAMIZ
    await init_db()
    
    # BOT TOKENINI TEKSHIRAMIZ
    token_preview = f"{BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}"
    logger.info(f"===> Bot professional rejimda ishga tushirildi. Token: {token_preview}")
    
    # WEBHOOKLARNI TOZALAYMIZ (muammolarni oldini olish uchun)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # POLLINGNI FONDA ISHGA TUSHIRAMIZ (Xizmatingiz darajasi: Super)
    # Bu usul Uptime Robot bilan birgalikda eng barqaror ishlaydi.
    polling_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("===> Bot polling (background task) boshlandi.")
    
    yield
    # TO'XTATISHDA TOZALASH
    polling_task.cancel()
    logger.info("===> Server to'xtatilmoqda.")

app = FastAPI(title='TriPro Admin API', lifespan=lifespan)

# Webhook endpoitlari endi kerak emas, lekin xato bermasligi uchun qoldiramiz 
# yoki o'chirib tashlagan ma'qul. Biz toza kod uchun o'chirib tashlaymiz.

@app.api_route('/', methods=['GET', 'HEAD'])
async def health():
    return {"status": "active", "service": "TriPro Professional Bot", "mode": "polling"}

# ──────────────────────────────────────────────
# Admin HTML
# ──────────────────────────────────────────────

ADMIN_HTML = str(Path(__file__).parent / 'admin.html')

@app.get('/admin', response_class=HTMLResponse)
async def admin_panel():
    return FileResponse(ADMIN_HTML)

# ──────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────

@app.get('/api/orders')
async def list_orders(type: Optional[str] = Query(None)):
    if type == 'akfa':
        return await get_all_akfa()
    elif type == 'profilaktika':
        return await get_all_prof()
    return await get_combined_orders()

@app.get('/api/orders/{order_id}')
async def get_order(order_id: str):
    o = await get_akfa_order(order_id)
    if not o:
        raise HTTPException(404, 'Order not found')
    return o

class AkfaStatus(BaseModel):
    status: str

@app.post('/api/akfa/{order_id}/status')
async def set_akfa_status(order_id: str, body: AkfaStatus):
    o = await update_akfa(order_id, body.status)
    if not o:
        raise HTTPException(404, 'Order not found')
    return {'ok': True, 'order': o}

class ProfStatus(BaseModel):
    status: str

@app.post('/api/profilaktika/{pk}/status')
async def set_prof_status(pk: int, body: ProfStatus):
    o = await update_prof(pk, body.status)
    if not o:
        raise HTTPException(404, 'Profilaktika record not found')
    uid = o.get('telegram_id')
    if uid and body.status in ('accepted', 'completed'):
        sm = {'accepted': '✅ Profilaktika xizmatingiz qabul qilindi. Tez orada mutaxassisimiz siz bilan bog\'lanadi.',
              'completed': '🏁 Profilaktika xizmatingiz yakunlandi. Xizmatimizdan foydalanganingiz uchun rahmat!'}
        try:
            await bot.send_message(uid, sm[body.status])
        except Exception as e:
            logger.warning(f'Failed to notify user {uid}: {e}')
    return {'ok': True, 'order': o}

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

if __name__ == '__main__':
    uvicorn.run('backend:app', host='0.0.0.0', port=PORT, reload=True)
