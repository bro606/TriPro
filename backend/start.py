import asyncio
import json
import logging
import os
from aiohttp import web
import httpx
from database import init_db, get_all_orders, get_pending_orders, get_order, confirm_order, update_status

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment Variables
PUBLIC_URL = os.environ.get('PUBLIC_URL', 'https://tripro.onrender.com')
PORT = int(os.environ.get('PORT', 8000))

async def keep_alive():
    """
    Pings the public URL every 5 minutes to prevent Render Free tier from sleeping.
    """
    await asyncio.sleep(30) # Wait for server to start
    ping_url = f"{PUBLIC_URL.rstrip('/')}/health"
    logger.info(f'Keep-alive active: Pinging {ping_url} every 5 minutes')
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(ping_url, timeout=10)
                logger.info(f'Keep-alive ping -> {r.status_code}')
            except Exception as e:
                logger.warning(f'Keep-alive ping failed: {e}')
            await asyncio.sleep(300) # 5 minutes

# ─── API HANDLERS ───
async def handle_health(request):
    return web.json_response({'status': 'ok', 'service': 'TriPro Bot API'})

async def handle_list_orders(request):
    orders = get_all_orders()
    return web.json_response(orders)

async def handle_list_pending(request):
    orders = get_pending_orders()
    return web.json_response(orders)

async def handle_get_order(request):
    oid = request.match_info.get('order_id', '')
    order = get_order(oid)
    if not order:
        return web.json_response({'error': 'Order not found'}, status=404)
    return web.json_response(order)

async def handle_confirm_order(request):
    oid = request.match_info.get('order_id', '')
    order = confirm_order(oid)
    if not order:
        return web.json_response({'error': 'Order not found'}, status=404)
    return web.json_response(order)

async def handle_update_status(request):
    oid = request.match_info.get('order_id', '')
    try:
        body = await request.json()
    except:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    
    new_status = body.get('status', '')
    order = update_status(oid, new_status)
    if not order:
        return web.json_response({'error': 'Order not found or invalid status'}, status=404)
    return web.json_response(order)

async def run_api():
    app = web.Application()
    # CORS setup
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == 'OPTIONS':
                response = web.Response()
            else:
                response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PATCH, DELETE'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        return middleware
    
    app.middlewares.append(cors_middleware)

    # Routes
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/orders', handle_list_orders)
    app.router.add_get('/api/orders/pending', handle_list_pending)
    app.router.add_get('/api/orders/{order_id}', handle_get_order)
    app.router.add_post('/api/orders/{order_id}/confirm', handle_confirm_order)
    app.router.add_post('/api/orders/{order_id}/status', handle_update_status)

    runner = web.AppRunner(app)
    await runner.setup()
    print(f"DEBUG: Port qiymati: {os.getenv('PORT')}")
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f'✅ API Server running on 0.0.0.0:{PORT}')
    return runner

async def main():
    # 1. Init Database
    init_db()
    
    # 2. Start API Server
    await run_api()
    
    # 3. Start Keep-Alive task
    asyncio.create_task(keep_alive())
    
    # 4. Start Telegram Bot
    from bot import bot_main
    logger.info("🚀 Starting Telegram Bot...")
    await bot_main()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}", exc_info=True)
