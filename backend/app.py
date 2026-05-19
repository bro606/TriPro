from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import init_db, get_all_orders, get_pending_orders, get_order, confirm_order, update_status

app = FastAPI(title='TriPro API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Mount static files (serve admin.html and index.html from parent dir)
import os
PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount('/admin', StaticFiles(directory=PARENT, html=True), name='admin')

# ─── MODELS ───
class StatusUpdate(BaseModel):
    status: str

# ─── ENDPOINTS ───
@app.on_event('startup')
def startup():
    init_db()

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

# ─── MAIN ───
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
