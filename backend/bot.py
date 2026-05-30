# TriPro Telegram Bot - Aiogram 3.x
# FSM: AKFA (9 bosqich) + Profilaktika (2 bosqich)
# SQLite ma'lumotlar bazasi: akfa_orders va profilaktika jadvallari

import asyncio, os, random, aiosqlite, logging
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = (os.getenv('BOT_TOKEN') or '8745687733:AAF_yQ-euksdfk2LfnmJXm_8Qaw0_yVqVpY').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Username')
SITE_URL = 'https://tri-pro-bro606s-projects.vercel.app'
BASE_DIR = Path(__file__).parent
LOCAL_DB = str(BASE_DIR / 'tripro.db')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ═══════════════════════════════════════════════
# FSM STATES
# ═══════════════════════════════════════════════

class AkfaForm(StatesGroup):
    name = State()
    surname = State()
    phone = State()
    material = State()
    glass_layer = State()
    profile_color = State()
    dimensions = State()
    quantity = State()
    confirm = State()

class ProfilaktikaForm(StatesGroup):
    location = State()
    time = State()

# ═══════════════════════════════════════════════
# SQLITE DATABASE
# ═══════════════════════════════════════════════

async def init_db():
    async with aiosqlite.connect(LOCAL_DB) as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS akfa_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            telegram_id INTEGER,
            name TEXT, surname TEXT, phone TEXT,
            material TEXT, glass_layer TEXT, profile_color TEXT,
            dimensions TEXT, quantity INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS profilaktika (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            name TEXT, surname TEXT, phone TEXT,
            location TEXT, time_slot TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await conn.commit()

async def _gen_oid():
    async with aiosqlite.connect(LOCAL_DB) as conn:
        async with conn.execute('SELECT order_id FROM akfa_orders WHERE order_id IS NOT NULL') as cursor:
            rows = await cursor.fetchall()
            ids = {r[0] for r in rows}
    
    for _ in range(100):
        oid = str(random.randint(10000, 99999))
        if oid not in ids:
            return oid
    return str(random.randint(10000, 99999))

async def save_akfa_order(tg, name, surname, phone, material, glass, color, dims, qty=1):
    oid = await _gen_oid()
    async with aiosqlite.connect(LOCAL_DB) as conn:
        await conn.execute('INSERT INTO akfa_orders (order_id,telegram_id,name,surname,phone,material,glass_layer,profile_color,dimensions,quantity) VALUES (?,?,?,?,?,?,?,?,?,?)',
                     (oid, tg, name, surname, phone, material, glass, color, dims, qty))
        await conn.commit()
    return oid

async def get_akfa_order(oid):
    async with aiosqlite.connect(LOCAL_DB) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute('SELECT * FROM akfa_orders WHERE order_id = ?', (oid,)) as cursor:
            r = await cursor.fetchone()
            return dict(r) if r else None

async def get_all_akfa():
    async with aiosqlite.connect(LOCAL_DB) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute('SELECT * FROM akfa_orders ORDER BY created_at DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_akfa(oid, status):
    if status not in ('pending','material_delivered','assembling','cutting','ready'):
        return None
    async with aiosqlite.connect(LOCAL_DB) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute('UPDATE akfa_orders SET status = ? WHERE order_id = ?', (status, oid))
        await conn.commit()
        async with conn.execute('SELECT * FROM akfa_orders WHERE order_id = ?', (oid,)) as cursor:
            r = await cursor.fetchone()
            return dict(r) if r else None

async def save_profilaktika(tg, name, surname, phone, location, time_slot):
    async with aiosqlite.connect(LOCAL_DB) as conn:
        await conn.execute('INSERT INTO profilaktika (telegram_id,name,surname,phone,location,time_slot) VALUES (?,?,?,?,?,?)',
                     (tg, name, surname, phone, location, time_slot))
        await conn.commit()

async def get_all_prof():
    async with aiosqlite.connect(LOCAL_DB) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute('SELECT * FROM profilaktika ORDER BY created_at DESC') as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_prof(pk, status):
    if status not in ('pending','accepted','completed'):
        return None
    async with aiosqlite.connect(LOCAL_DB) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute('UPDATE profilaktika SET status = ? WHERE id = ?', (status, pk))
        await conn.commit()
        async with conn.execute('SELECT * FROM profilaktika WHERE id = ?', (pk,)) as cursor:
            r = await cursor.fetchone()
            return dict(r) if r else None

async def get_combined_orders():
    res = []
    akfa = await get_all_akfa()
    for o in akfa:
        res.append({'id':f'akfa_{o["id"]}','pk':o['id'],'type':'akfa',
            'order_id':o['order_id'] or '','client':f"{o['name'] or ''} {o['surname'] or ''}".strip() or str(o['telegram_id']),
            'phone':o['phone'] or '','info':f"Material: {o['material']}, Oyna: {o['glass_layer']}, Rang: {o['profile_color']}, O'lcham: {o['dimensions']}, Soni: {o['quantity']}",
            'status':o['status'],'created_at':o['created_at']})
    prof = await get_all_prof()
    for p in prof:
        res.append({'id':f'prof_{p["id"]}','pk':p['id'],'type':'profilaktika','order_id':'',
            'client':f"{p['name'] or ''} {p['surname'] or ''}".strip() or str(p['telegram_id']),
            'phone':p['phone'] or '','info':f"Manzil: {p['location']}, Vaqt: {p['time_slot']}",
            'status':p['status'],'created_at':p['created_at']})
    res.sort(key=lambda x: x['created_at'], reverse=True)
    return res

# ═══════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════

BACK = '🔙 Bosh menyuga'

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 Saytni ko\'rish', url=SITE_URL)],
        [InlineKeyboardButton(text='🪟 AKFA buyurtmasi', callback_data='new_order')],
        [InlineKeyboardButton(text='🔍 ID tekshirish', callback_data='check_order')],
        [InlineKeyboardButton(text='🛠 Boshqa xizmatlar', callback_data='other_services')],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BACK, callback_data='to_menu')],
    ])

def phone_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='📱 Kontaktni ulash', request_contact=True)],
        [KeyboardButton(text='⌨️ Raqamni yozish')],
        [KeyboardButton(text=BACK)]], resize_keyboard=True, one_time_keyboard=True)

def mat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Plastik', callback_data='mp')],
        [InlineKeyboardButton(text='Alyumin', callback_data='ma')],
        [InlineKeyboardButton(text=BACK, callback_data='to_menu')]])

def glass_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='1 qavatli', callback_data='g1')],
        [InlineKeyboardButton(text='2 qavatli', callback_data='g2')],
        [InlineKeyboardButton(text=BACK, callback_data='to_menu')]])

def color_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Oq', callback_data='coq')],
        [InlineKeyboardButton(text='Jigarrang', callback_data='cji')],
        [InlineKeyboardButton(text='Antratsit', callback_data='cant')],
        [InlineKeyboardButton(text='Boshqa', callback_data='cbosh')],
        [InlineKeyboardButton(text=BACK, callback_data='to_menu')]])

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Tasdiqlash', callback_data='cy')],
        [InlineKeyboardButton(text='❌ Qaytadan', callback_data='cr')]])

def other_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👨‍💻 Admin bilan bog\'lanish', url=f'https://t.me/{ADMIN_USERNAME}')],
        [InlineKeyboardButton(text='🛡 Profilaktikaga yozilish', callback_data='np')],
        [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='to_menu')]])

def loc_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='📍 Joylashuvni yuborish', request_location=True)],
        [KeyboardButton(text='✏️ Manzilni yozish')],
        [KeyboardButton(text=BACK)]], resize_keyboard=True, one_time_keyboard=True)

def time_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='09:00 - 11:00', callback_data='t0900')],
        [InlineKeyboardButton(text='11:00 - 13:00', callback_data='t1100')],
        [InlineKeyboardButton(text='14:00 - 16:00', callback_data='t1400')],
        [InlineKeyboardButton(text='16:00 - 18:00', callback_data='t1600')],
        [InlineKeyboardButton(text=BACK, callback_data='to_menu')]])

def offer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛡 Profilaktikaga yozilish', callback_data='np')],
        [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='to_menu')]])

# ═══════════════════════════════════════════════
# START / CANCEL
# ═══════════════════════════════════════════════

@dp.message(Command('start'))
async def start(m: types.Message):
    await m.answer(
        f'Assalomu alaykum, {m.from_user.first_name or "Foydalanuvchi"}! '
        f'TriPro ustaxonasiga xush kelibsiz. '
        f'Biz sizga sifatli AKFA romlar, yog\'och va shisha mahsulotlarini yetkazib beramiz.',
        reply_markup=main_kb())

@dp.message(Command('cancel'))
@dp.message(Command('bosh_menu'))
async def cancel(m: types.Message, s: FSMContext):
    await s.clear()
    await m.answer('Asosiy menyu:', reply_markup=main_kb())

# ═══════════════════════════════════════════════
# MENU CALLBACKS
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'to_menu')
async def to_menu(c: types.CallbackQuery, s: FSMContext):
    try:
        await c.answer()
        await s.clear()
        await c.message.edit_text('Asosiy menyu:', reply_markup=main_kb())
    except Exception as e:
        logger.error(f"Error in to_menu: {e}")

@dp.callback_query(F.data == 'new_order')
async def new_order(c: types.CallbackQuery, s: FSMContext):
    try:
        await c.answer()
        await s.set_state(AkfaForm.name)
        await c.message.edit_text('Buyurtma berish uchun savollarga javob bering.\n\n1/9: Ismingizni kiriting:', reply_markup=back_kb())
    except Exception as e:
        logger.error(f"Error in new_order: {e}")

@dp.callback_query(F.data == 'other_services')
async def other_svc(c: types.CallbackQuery, s: FSMContext):
    try:
        await c.answer()
        await c.message.edit_text(
            '🛠 Yog\'och mahsulotlari va shisha xizmatlari\n\n'
            'Siz tanlagan yo\'nalish bo\'yicha buyurtmalar individual tartibda qabul qilinadi. '
            'Aniq narxlar va dizayn masalalari bo\'yicha bizning bosh mutaxassisimiz bilan bevosita bog\'laning.\n\n'
            'Shuningdek, yilda bir marta profilaktika xizmatimizdan foydalanishingiz mumkin.',
            reply_markup=other_kb())
    except Exception as e:
        logger.error(f"Error in other_svc: {e}")

# ═══════════════════════════════════════════════
# AKFA FSM
# ═══════════════════════════════════════════════

@dp.message(AkfaForm.name, lambda m: m.text and m.text.strip())
async def p_name(m: types.Message, s: FSMContext):
    await s.update_data(name=m.text.strip())
    await s.set_state(AkfaForm.surname)
    await m.answer('2/9: Familiyangizni kiriting:', reply_markup=back_kb())

@dp.message(AkfaForm.name)
async def p_name_i(m: types.Message):
    await m.answer('Iltimos, ismingizni yozing:', reply_markup=back_kb())

@dp.message(AkfaForm.surname, lambda m: m.text and m.text.strip())
async def p_surname(m: types.Message, s: FSMContext):
    await s.update_data(surname=m.text.strip())
    await s.set_state(AkfaForm.phone)
    await m.answer('3/9: Telefon raqamingizni yuboring.\n\n"📱 Kontaktni ulash" tugmasini bosing yoki "⌨️ Raqamni yozish" ni tanlang:', reply_markup=phone_kb())

@dp.message(AkfaForm.surname)
async def p_surname_i(m: types.Message):
    await m.answer('Iltimos, familiyangizni yozing:', reply_markup=back_kb())

@dp.message(AkfaForm.phone, F.contact)
async def p_ph_contact(m: types.Message, s: FSMContext):
    await s.update_data(phone=m.contact.phone_number)
    await s.set_state(AkfaForm.material)
    await m.answer('4/9: Material turini tanlang:', reply_markup=mat_kb())

@dp.message(AkfaForm.phone, F.text == '⌨️ Raqamni yozish')
async def p_ph_manual(m: types.Message, s: FSMContext):
    await m.answer('Telefon raqamingizni kiriting (masalan: +998901234567):', reply_markup=back_kb())

@dp.message(AkfaForm.phone, lambda m: m.text and len(m.text.strip()) > 5 and m.text.strip() != BACK)
async def p_ph_text(m: types.Message, s: FSMContext):
    await s.update_data(phone=m.text.strip())
    await s.set_state(AkfaForm.material)
    await m.answer('4/9: Material turini tanlang:', reply_markup=mat_kb())

@dp.message(AkfaForm.phone, F.text == BACK)
async def p_ph_back(m: types.Message, s: FSMContext):
    await s.clear(); await m.answer('Asosiy menyu:', reply_markup=main_kb())

@dp.message(AkfaForm.phone)
async def p_ph_inv(m: types.Message):
    await m.answer('Iltimos, kontakt tugmasini bosing yoki raqamingizni yozing:', reply_markup=phone_kb())

@dp.callback_query(AkfaForm.material, lambda c: c.data in ('mp','ma'))
async def p_mat(c: types.CallbackQuery, s: FSMContext):
    await c.answer()
    await s.update_data(material={'mp':'Plastik','ma':'Alyumin'}[c.data])
    await s.set_state(AkfaForm.glass_layer)
    await c.message.edit_text('5/9: Oyna qavatini tanlang:', reply_markup=glass_kb())

@dp.callback_query(AkfaForm.glass_layer, lambda c: c.data in ('g1','g2'))
async def p_glass(c: types.CallbackQuery, s: FSMContext):
    await c.answer()
    await s.update_data(glass_layer={'g1':'1 qavatli','g2':'2 qavatli'}[c.data])
    await s.set_state(AkfaForm.profile_color)
    await c.message.edit_text('6/9: Profil rangini tanlang:', reply_markup=color_kb())

@dp.callback_query(AkfaForm.profile_color, lambda c: c.data in ('coq','cji','cant','cbosh'))
async def p_color(c: types.CallbackQuery, s: FSMContext):
    await c.answer()
    await s.update_data(profile_color={'coq':'Oq','cji':'Jigarrang','cant':'Antratsit','cbosh':'Boshqa'}[c.data])
    await s.set_state(AkfaForm.dimensions)
    await c.message.delete()
    await c.message.answer('7/9: Taxminiy o\'lchamlarni yozing (masalan: 80x90):', reply_markup=back_kb())

@dp.message(AkfaForm.dimensions, lambda m: m.text and m.text.strip())
async def p_dim(m: types.Message, s: FSMContext):
    await s.update_data(dimensions=m.text.strip())
    await s.set_state(AkfaForm.quantity)
    await m.answer('8/9: Mahsulot sonini yozing (masalan: 2):', reply_markup=back_kb())

@dp.message(AkfaForm.dimensions)
async def p_dim_i(m: types.Message):
    await m.answer('Iltimos, o\'lchamlarni yozing (masalan: 80x90):', reply_markup=back_kb())

@dp.message(AkfaForm.quantity, lambda m: m.text and m.text.strip().isdigit() and int(m.text.strip()) > 0)
async def p_qty(m: types.Message, s: FSMContext):
    await s.update_data(quantity=int(m.text.strip()))
    d = await s.get_data()
    txt = (f'📋 Buyurtmangiz tasdiqlash uchun tayyor:\n\n'
           f'👤 Ism: {d["name"]} {d["surname"]}\n📞 Telefon: {d["phone"]}\n'
           f'🛠 Material: {d["material"]}\n🪟 Oyna qavati: {d["glass_layer"]}\n'
           f'🎨 Rang: {d["profile_color"]}\n📐 O\'lcham: {d["dimensions"]}\n'
           f'📦 Soni: {d["quantity"]} ta\n\nHammasi to\'g\'rimi?')
    await s.set_state(AkfaForm.confirm)
    await m.answer(txt, reply_markup=confirm_kb())

@dp.message(AkfaForm.quantity)
async def p_qty_i(m: types.Message):
    await m.answer('Iltimos, musbat son kiriting (masalan: 2):', reply_markup=back_kb())

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'cy')
async def p_yes(c: types.CallbackQuery, s: FSMContext):
    await c.answer()
    d = await s.get_data()
    oid = await save_akfa_order(c.from_user.id, d.get('name',''), d.get('surname',''), d.get('phone',''),
                          d.get('material',''), d.get('glass_layer',''), d.get('profile_color',''),
                          d.get('dimensions',''), d.get('quantity',1))
    await s.clear()
    await c.message.edit_text(
        f'✅ Buyurtmangiz qabul qilindi. ID: {oid}\n\n'
        f'👤 Ism: {d["name"]} {d["surname"]}\n📞 Telefon: {d["phone"]}\n'
        f'🛠 Material: {d["material"]}\n🪟 Oyna qavati: {d["glass_layer"]}\n'
        f'🎨 Rang: {d["profile_color"]}\n📐 O\'lcham: {d["dimensions"]}\n'
        f'📦 Soni: {d["quantity"]} ta\n\nMutaxassisimiz tez orada siz bilan bog\'lanadi.',
        reply_markup=main_kb())
    await c.message.answer(
        '🛡 Yilda bir marta profilaktika xizmatimizdan foydalaning!\nDeraza va romlaringizni tekshirib, xizmat ko\'rsatamiz.',
        reply_markup=offer_kb())

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'cr')
async def p_no(c: types.CallbackQuery, s: FSMContext):
    await c.answer(); await s.clear()
    await s.set_state(AkfaForm.name)
    await c.message.edit_text('Buyurtma berish uchun savollarga javob bering.\n\n1/9: Ismingizni kiriting:', reply_markup=back_kb())

# ═══════════════════════════════════════════════
# ID CHECK
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'check_order')
async def chk(c: types.CallbackQuery, s: FSMContext):
    try:
        await c.answer()
        await c.message.edit_text('Buyurtmangizni tekshirish uchun 5 xonali ID raqamingizni kiriting:', reply_markup=back_kb())
        await s.set_state('chk')
    except Exception as e:
        logger.error(f"Error in check_order: {e}")

@dp.message(StateFilter('chk'))
async def chk_id(m: types.Message, s: FSMContext):
    oid = m.text.strip()
    if not oid.isdigit() or len(oid) != 5:
        await m.answer('Iltimos, to\'g\'ri 5 xonali ID kiriting (masalan: 54921):', reply_markup=back_kb()); return
    o = await get_akfa_order(oid)
    if not o:
        await m.answer('❌ Bunday ID topilmadi.', reply_markup=main_kb()); await s.clear(); return
    sm = {'pending':'⏳ Kutilmoqda','material_delivered':'🚚 Material olib kelindi','assembling':'🔧 Yig\'ilmoqda','cutting':'🪟 Oyna kesilmoqda','ready':'📦 Tayyor va yetkazilmoqda'}
    await m.answer(
        f'🔍 Buyurtma ID: {o["order_id"]}\n\n'
        f'👤 Ism: {o["name"]} {o["surname"]}\n📞 Telefon: {o["phone"]}\n'
        f'🛠 Material: {o["material"]}\n🪟 Oyna qavati: {o["glass_layer"]}\n'
        f'🎨 Rang: {o["profile_color"]}\n📐 O\'lcham: {o["dimensions"]}\n'
        f'📦 Soni: {o["quantity"]} ta\n📊 Holati: {sm.get(o["status"],o["status"])}\n'
        f'📅 Yaratilgan: {o["created_at"]}', reply_markup=main_kb())
    await s.clear()

# ═══════════════════════════════════════════════
# PROFILAKTIKA
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'np')
async def np_start(c: types.CallbackQuery, s: FSMContext):
    try:
        await c.answer()
        await s.set_state(ProfilaktikaForm.location)
        await c.message.edit_text('🛡 Profilaktika xizmati\n\nManzilingizni yuboring yoki yozing (masalan: Farg\'ona sh., Navoiy ko\'ch. 15):', reply_markup=loc_kb())
    except Exception as e:
        logger.error(f"Error in np_start: {e}")

@dp.message(ProfilaktikaForm.location, F.location)
async def np_loc_share(m: types.Message, s: FSMContext):
    await s.update_data(location=f'{m.location.latitude}, {m.location.longitude}')
    await s.set_state(ProfilaktikaForm.time)
    await m.answer('Qulay vaqtni tanlang:', reply_markup=time_kb())

@dp.message(ProfilaktikaForm.location, F.text == '✏️ Manzilni yozish')
async def np_loc_manual(m: types.Message, s: FSMContext):
    await m.answer('Manzilingizni yozing (masalan: Farg\'ona sh., Navoiy ko\'ch. 15):', reply_markup=back_kb())

@dp.message(ProfilaktikaForm.location, lambda m: m.text and len(m.text.strip()) > 3 and m.text.strip() != BACK)
async def np_loc_text(m: types.Message, s: FSMContext):
    await s.update_data(location=m.text.strip())
    await s.set_state(ProfilaktikaForm.time)
    await m.answer('Qulay vaqtni tanlang:', reply_markup=time_kb())

@dp.message(ProfilaktikaForm.location, F.text == BACK)
async def np_loc_back(m: types.Message, s: FSMContext):
    await s.clear(); await m.answer('Asosiy menyu:', reply_markup=main_kb())

@dp.message(ProfilaktikaForm.location)
async def np_loc_inv(m: types.Message):
    await m.answer('Iltimos, joylashuv yuboring yoki manzilni yozing:', reply_markup=loc_kb())

@dp.callback_query(ProfilaktikaForm.time, lambda c: c.data.startswith('t'))
async def np_time(c: types.CallbackQuery, s: FSMContext):
    await c.answer()
    tm = {'t0900':'09:00 - 11:00','t1100':'11:00 - 13:00','t1400':'14:00 - 16:00','t1600':'16:00 - 18:00'}
    ts = tm[c.data]
    d = await s.get_data()
    u = c.from_user
    await save_profilaktika(u.id, u.first_name or '', u.last_name or '', '', d.get('location',''), ts)
    await s.clear()
    await c.message.edit_text(
        f'✅ Profilaktika xizmatiga yozildingiz!\n\n📍 Manzil: {d["location"]}\n⏰ Vaqt: {ts}\n\nMutaxassisimiz belgilangan vaqtda siz bilan bog\'lanadi.',
        reply_markup=main_kb())

@dp.callback_query(ProfilaktikaForm.time, lambda c: c.data == 'to_menu')
async def np_time_back(c: types.CallbackQuery, s: FSMContext):
    await c.answer(); await s.clear()
    await c.message.edit_text('Asosiy menyu:', reply_markup=main_kb())

# ═══════════════════════════════════════════════
# BOT START
# ═══════════════════════════════════════════════

async def bot_main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info('Bot polling...')
    await dp.start_polling(bot)

async def run_bot():
    await init_db()
    await bot_main()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass
