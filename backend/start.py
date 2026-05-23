import asyncio
import json
import logging
import os
from aiohttp import web

import httpx
from database import get_all_orders, get_order, confirm_order, update_status

logger = logging.getLogger(__name__)

PUBLIC_URL = os.environ.get('PUBLIC_URL', '')
PORT = int(os.environ.get('PORT', 8000))

async def keep_alive():
    if not PUBLIC_URL:
        logger.info('PUBLIC_URL not set — keep-alive disabled')
        return
    logger.info(f'Keep-alive started, pinging {PUBLIC_URL} every 5 min')
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(300)
            try:
                r = await client.get(PUBLIC_URL, timeout=10)
                logger.info(f'Keep-alive ping -> {r.status_code}')
            except Exception as e:
                logger.warning(f'Keep-alive ping failed: {e}')

async def handle_health(request):
    return web.json_response({'status': 'ok'})

async def handle_list_orders(request):
    orders = get_all_orders()
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
    body = await request.json()
    new_status = body.get('status', '')
    order = update_status(oid, new_status)
    if not order:
        return web.json_response({'error': 'Order not found or invalid status'}, status=404)
    return web.json_response(order)

async def run_api():
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/orders', handle_list_orders)
    app.router.add_get('/api/orders/{order_id}', handle_get_order)
    app.router.add_post('/api/orders/{order_id}/confirm', handle_confirm_order)
    app.router.add_post('/api/orders/{order_id}/status', handle_update_status)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f'HTTP server running on 0.0.0.0:{PORT}')
    return runner

async def main():
    await run_api()
    asyncio.create_task(keep_alive())
    from bot import main as bot_main
    await bot_main()

if __name__ == '__main__':
    asyncio.run(main())
