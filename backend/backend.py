# TriPro FastAPI Backend - admin panel uchun
import asyncio, os, json, threading
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from bot import bot, dp, bot_main, get_akfa_order, get_all_akfa, update_akfa, get_all_prof, update_prof, get_combined_orders, init_db, logger

PORT = int(os.getenv('PORT', '10000'))

init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Botni alohida taskda ishga tushiramiz
    bot_task = asyncio.create_task(bot_main())
    logger.info("Telegram Bot backgroundda ishga tushdi.")
    yield
    # To'xtatishda botni yopamiz
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        logger.info("Telegram Bot to'xtatildi.")

app = FastAPI(title='TriPro Admin API', lifespan=lifespan)

class StatusUpdate(BaseModel):
    status: str

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
        return get_all_akfa()
    elif type == 'profilaktika':
        return get_all_prof()
    return get_combined_orders()

@app.get('/api/orders/{order_id}')
async def get_order(order_id: str):
    o = get_akfa_order(order_id)
    if not o:
        raise HTTPException(404, 'Order not found')
    return o

class AkfaStatus(BaseModel):
    status: str

@app.post('/api/akfa/{order_id}/status')
async def set_akfa_status(order_id: str, body: AkfaStatus):
    o = update_akfa(order_id, body.status)
    if not o:
        raise HTTPException(404, 'Order not found')
    return {'ok': True, 'order': o}

class ProfStatus(BaseModel):
    status: str

@app.post('/api/profilaktika/{pk}/status')
async def set_prof_status(pk: int, body: ProfStatus):
    o = update_prof(pk, body.status)
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
