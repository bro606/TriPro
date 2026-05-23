# Render.com-da Botni sozlash bo'yicha to'liq qo'llanma

Sizning botingiz yangi token (`8745687733:AAGcftZHiq3jZkyvWN6IZglvyxz26kJ5G-4`) bilan muvaffaqiyatli ishga tushishi uchun quyidagi qadamlarni diqqat bilan bajaring.

## 1. Render Dashboard-ga kiring
Render.com-dagi loyihangizga kiring va **Settings** bo'limini oching.

## 2. Start Command (Ishga tushirish buyrug'i)
"Start Command" qatorida mana bu kod yozilganligiga ishonch hosil qiling:
`python backend/start.py`

*(Agar sizda faqat `python start.py` bo'lsa, u ishlamasligi mumkin, chunki fayl `backend` papkasi ichida joylashgan).*

## 3. Environment Variables (Muhit o'zgaruvchilari)
**Environment** bo'limida quyidagi o'zgaruvchilarni qo'shing (yoki bor bo'lsa yangilang):

| Name (Nomi) | Value (Qiymati) |
| :--- | :--- |
| `BOT_TOKEN` | `8745687733:AAGcftZHiq3jZkyvWN6IZglvyxz26kJ5G-4` |
| `PUBLIC_URL` | `https://tripro.onrender.com` |
| `PORT` | `8000` |

## 4. Kodni GitHub-ga yuklash (Push)
Men hozirgina kodni kompyuteringizda to'g'irladim (yangi token va `start.py` fayli). Bu o'zgarishlar Render-ga borishi uchun siz ularni GitHub-ga **Push** qilishingiz kerak:
1. Terminalda: `git add .`
2. Terminalda: `git commit -m "update bot token and start script"`
3. Terminalda: `git push origin main` (yoki master)

## Nima uchun 502 xatosi beryapti?
Render loyihangizni "Web Service" deb hisoblaydi. Agar u 1 daqiqa ichida portdan javob olmasa (ya'ni `start.py` ishga tushib portni band qilmasa), u "502 Bad Gateway" xatosini beradi. 

**Sabablari:**
- `Start Command` noto'g'ri ko'rsatilgan.
- Kodda xatolik bor (masalan, token topilmagan).
- Kutubxonalar o'rnatilmagan (`requirements.txt` yangilangan bo'lishi shart).

Men barcha kodlarni to'g'irladim, faqat ularni GitHub-ga yuklab, Render-da `Start Command`ni tekshirib qo'ysangiz bo'ldi.
