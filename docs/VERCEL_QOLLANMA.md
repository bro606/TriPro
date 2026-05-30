# Vercel-ga o'tish bo'yicha qo'llanma

Netlify limiti tugaganligi sababli, loyihani Vercel-ga o'tkazish tavsiya etiladi. Men barcha kerakli sozlamalarni (`vercel.json`) tayyorlab qo'ydim.

## 1. Vercel-ga kirish
1. [vercel.com](https://vercel.com) saytiga kiring.
2. GitHub hisobingiz orqali ro'yxatdan o'ting yoki kiring.

## 2. Yangi loyiha qo'shish
1. **Add New...** -> **Project** tugmasini bosing.
2. GitHub-dagi `TriPro` repozitoriyasini tanlang va **Import** bosing.

## 3. Loyihani sozlash
1. **Framework Preset:** `Other` (yoki avtomatik aniqlaydi).
2. **Root Directory:** `./` (o'zgarishsiz qoladi).
3. **Build and Output Settings:** O'zgartirish shart emas, chunki loyiha statik.
4. **Environment Variables:** Hozircha shart emas (agar backend manzili o'zgarmasa).

## 4. Deploy (Nashr qilish)
1. **Deploy** tugmasini bosing.
2. Vercel sizga yangi manzil (masalan: `tripro.vercel.app`) beradi.

## Men nimalarni o'zgartirdim:
1. `netlify.toml` faylini o'chirib tashladim.
2. `vercel.json` faylini yaratdim. Bu fayl quyidagilarni ta'minlaydi:
   - `/admin` deb yozganda `admin.html` ochiladi.
   - Sahifa yangilanganda "404 Not Found" xatosi chiqmaydi.
   - URL-lar chiroyli ko'rinadi (`.html` qo'shimchasisiz).

Endi siz faqat o'zgarishlarni GitHub-ga yuklab (Push), Vercel-da loyihani ulashingiz kifoya.

---
**GitHub-ga yuklash buyruqlari:**
```powershell
git add .
git commit -m "Move to Vercel"
git push origin main
```
