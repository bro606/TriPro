import asyncio
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import init_db, get_all_orders, get_pending_orders, get_order, confirm_order, update_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='TriPro API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ─── MODELS ───
class StatusUpdate(BaseModel):
    status: str

# ─── ENDPOINTS ───
@app.get('/health')
@app.get('/')
def health():
    return {"status": "ok", "service": "TriPro API + Bot"}

@app.get('/api/orders')
def list_orders():
    return JSONResponse(get_all_orders())

@app.get('/api/orders/pending')
def list_pending():
    return JSONResponse(get_pending_orders())

@app.get('/api/orders/{order_id}')
def get_order_by_id(order_id: str):
    order = get_order(order_id)
    if not order:
        raise HTTPException(404, 'Order not found')
    return JSONResponse(order)

@app.post('/api/orders/{order_id}/confirm')
def confirm(order_id: str):
    order = confirm_order(order_id)
    if not order:
        raise HTTPException(404, 'Order not found')
    return JSONResponse(order)

@app.post('/api/orders/{order_id}/status')
def change_status(order_id: str, body: StatusUpdate):
    order = update_status(order_id, body.status)
    if not order:
        raise HTTPException(404, 'Order not found or invalid status')
    return JSONResponse(order)

# ─── BOT STARTUP ───
@app.on_event('startup')
async def startup_event():
    init_db()
    from bot import bot_main
    # Start bot polling in the background
    asyncio.create_task(bot_main())
    logger.info("Bot started in background via FastAPI startup")

# ─── MAIN ───
if __name__ == '__main__':
    import uvicorn
    PORT = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=PORT)
