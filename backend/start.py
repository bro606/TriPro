import os
import uvicorn
import sys

# Script joylashgan katalogni PYTHONPATH ga qo'shamiz
# Bu 'bot' va 'backend' modullarini import qilishda xatolik chiqmasligi uchun kerak
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from backend import app

if __name__ == "__main__":
    # Render tomonidan berilgan PORT ni olamiz, aks holda 8000
    port = int(os.getenv("PORT", 8000))
    
    print(f"Server {port} portida ishga tushmoqda...")
    uvicorn.run(app, host="0.0.0.0", port=port)
