import asyncio
import threading
import logging
import os
import httpx
import uvicorn

logger = logging.getLogger(__name__)

PUBLIC_URL = os.environ.get('PUBLIC_URL', '')

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

def run_api():
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run('app:app', host='0.0.0.0', port=port, log_level='info')

async def main():
    asyncio.create_task(keep_alive())
    t = threading.Thread(target=run_api, daemon=True)
    t.start()
    from bot import main as bot_main
    await bot_main()

if __name__ == '__main__':
    asyncio.run(main())
