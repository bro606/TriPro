import asyncio
import threading
import uvicorn

def run_api():
    uvicorn.run('app:app', host='0.0.0.0', port=8000, log_level='info')

async def main():
    t = threading.Thread(target=run_api, daemon=True)
    t.start()
    from bot import main as bot_main
    await bot_main()

if __name__ == '__main__':
    asyncio.run(main())
