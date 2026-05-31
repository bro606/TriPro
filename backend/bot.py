import asyncio, os, random, logging, time
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, StateFilter, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ErrorEvent, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage
from typing import Any, Awaitable, Callable, Dict

# Yangi database modulidan import
from .database import (
    init_db, save_akfa_order, get_akfa_order, save_maintenance_request, 
    save_user, get_orders_for_maintenance
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'TriPro_Admin')
SITE_URL = 'https://tripro.vercel.app'
BASE_DIR = Path(__file__).parent
LOCAL_DB = str(BASE_DIR / 'tripro.db')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ═══════════════════════════════════════════════
# MIDDLEWARES (Throttling / Anti-Flood)
# ═══════════════════════════════════════════════

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slow_mode_delay: float = 0.5):
        self.users = {}
        self.delay = slow_mode_delay
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get('event_from_user')
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        now = time.time()
        
        if user_id in self.users:
            last_time = self.users[user_id]
            if now - last_time < self.delay:
                # Agar foydalanuvchi juda tez bosayotgan bo'lsa, javob bermaymiz
                return
        
        self.users[user_id] = now
        return await handler(event, data)

# Middleware vaqtincha o'chirildi (Anti-flood muammosini istisno qilish uchun)
# dp.message.middleware(ThrottlingMiddleware())
# dp.callback_query.middleware(ThrottlingMiddleware())

# ═══════════════════════════════════════════════
# GLOBAL ERROR HANDLER
# ═══════════════════════════════════════════════

@dp.error()
async def error_handler(event: ErrorEvent):
    logger.error(f"❌ KUTILMAGAN XATO: {event.exception}", exc_info=True)
    try:
        if event.update.callback_query:
            await event.update.callback_query.answer("⚠️ Texnik xatolik! Qaytadan urinib ko'ring.", show_alert=True)
        elif event.update.message:
            await event.update.message.answer("⚠️ Kechirasiz, xatolik yuz berdi. Iltimos, /start bosing.")
    except Exception as e:
        logger.error(f"Error handler xatosi: {e}")

# ═══════════════════════════════════════════════
# FSM STATES
# ═══════════════════════════════════════════════

class AkfaForm(StatesGroup):
    name = State()
    surname = State()
    phone = State()
    material = State()
    glass_layer = State()
    glass_color = State()
    glass_pattern = State()
    profile_color = State()
    dimensions = State()
    quantity = State()
    confirm = State()

class MaintenanceForm(StatesGroup):
    problem = State()

class ProfilaktikaForm(StatesGroup):
    location = State()
    time = State()

# Database logic is now in database.py

# ═══════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════

BACK = '🔙 Bosh menyuga'

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 Saytni ko\'rish', url=SITE_URL)],
        [InlineKeyboardButton(text='🪟 AKFA buyurtmasi', callback_data='new_order')],
        [InlineKeyboardButton(text='🔍 ID tekshirish', callback_data='check_order')],
        [InlineKeyboardButton(text='🛠 Usta chaqirish', callback_data='call_master')],
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

# ═══════════════════════════════════════════════
# GLOBAL HANDLERS (BASH MENU MUAMMOSI YECHIMI)
# ═══════════════════════════════════════════════

@dp.message(F.text == BACK)
@dp.message(Command('cancel'))
@dp.message(Command('bosh_menu'))
async def cancel_any(m: types.Message, state: FSMContext):
    """Barcha holatlarda (FSM ichida bo'lsa ham) ishlaydi va menyuga qaytaradi"""
    await state.clear()
    await m.answer('🤖 **Asosiy menyu:**', reply_markup=ReplyKeyboardRemove())
    await m.answer('Quyidagi xizmatlardan birini tanlang:', reply_markup=main_kb(), parse_mode='Markdown')

@dp.message(Command('start'))
async def start(m: types.Message):
    await save_user(m.from_user.id, m.from_user.username, m.from_user.first_name, m.from_user.last_name)
    await m.answer(
        f'Assalomu alaykum, {m.from_user.first_name or "Foydalanuvchi"}! '
        f'TriPro ustaxonasiga xush kelibsiz.',
        reply_markup=main_kb())

@dp.callback_query(F.data == 'to_menu')
async def to_menu(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    await c.message.answer('🤖 **Asosiy menyu:**', reply_markup=main_kb(), parse_mode='Markdown')
    await c.message.delete()

@dp.callback_query(F.data == 'new_order')
async def new_order(c: types.CallbackQuery, state: FSMContext):
    try:
        await c.answer()
        await state.set_state(AkfaForm.name)
        await c.message.edit_text('🏗 **Yangi buyurtma yaratish**\n\n👤 **Ismingizni kiriting:**', reply_markup=back_kb(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in new_order: {e}")

@dp.callback_query(F.data == 'other_services')
async def other_svc(c: types.CallbackQuery, state: FSMContext):
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
async def p_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(AkfaForm.surname)
    await m.answer('👤 **Familiyangizni kiriting:**', reply_markup=back_kb(), parse_mode='Markdown')

@dp.message(AkfaForm.surname, lambda m: m.text and m.text.strip())
async def p_surname(m: types.Message, state: FSMContext):
    await state.update_data(surname=m.text.strip())
    await state.set_state(AkfaForm.phone)
    await m.answer('📱 **Telefon raqamingizni yuboring:**', reply_markup=phone_kb(), parse_mode='Markdown')

@dp.message(AkfaForm.phone, F.contact)
async def p_ph_contact(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number)
    await state.set_state(AkfaForm.material)
    await m.answer('🏗️ **Material turini tanlang:**', reply_markup=mat_kb(), parse_mode='Markdown')

@dp.message(AkfaForm.phone, lambda m: m.text and len(m.text.strip()) > 5 and m.text.strip() != BACK)
async def p_ph_text(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text.strip())
    await state.set_state(AkfaForm.material)
    await m.answer('🏗️ **Material turini tanlang:**', reply_markup=mat_kb(), parse_mode='Markdown')

@dp.callback_query(AkfaForm.material, lambda c: c.data in ('mp','ma'))
async def p_mat(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.update_data(material={'mp':'Plastik','ma':'Alyumin'}[c.data])
    await state.set_state(AkfaForm.glass_layer)
    await c.message.edit_text('🪟 **Oyna qavatini tanlang:**', reply_markup=glass_kb(), parse_mode='Markdown')

@dp.callback_query(AkfaForm.glass_layer, lambda c: c.data in ('g1','g2'))
async def p_glass(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.update_data(glass_layer={'g1':'1 qavatli','g2':'2 qavatli'}[c.data])
    await state.set_state(AkfaForm.glass_color)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚪ Oq", callback_data="co_oq"), InlineKeyboardButton(text="⚫ Qora", callback_data="co_qora")],
        [InlineKeyboardButton(text="🟤 Jigarrang", callback_data="co_jig"), InlineKeyboardButton(text=BACK, callback_data="to_menu")]
    ])
    await c.message.edit_text('🎨 **Oyna rangini tanlang:**', reply_markup=kb, parse_mode='Markdown')

@dp.callback_query(AkfaForm.glass_color, lambda c: c.data.startswith('co_'))
async def p_glass_color(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    colors = {"co_oq":"Oq", "co_qora":"Qora", "co_jig":"Jigarrang"}
    await state.update_data(glass_color=colors[c.data])
    await state.set_state(AkfaForm.glass_pattern)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Gulli", callback_data="p_gulli"), InlineKeyboardButton(text="🖼️ Oddiy (gulsiz)", callback_data="p_oddiy")],
        [InlineKeyboardButton(text=BACK, callback_data="to_menu")]
    ])
    await c.message.edit_text('✨ **Oyna ko\'rinishini tanlang:**', reply_markup=kb, parse_mode='Markdown')

@dp.callback_query(AkfaForm.glass_pattern, lambda c: c.data.startswith('p_'))
async def p_glass_pattern(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    patterns = {"p_gulli":"Gulli", "p_oddiy":"Oddiy (gulsiz)"}
    await state.update_data(glass_pattern=patterns[c.data])
    await state.set_state(AkfaForm.profile_color)
    await c.message.edit_text('🖌️ **Profil rangini tanlang:**', reply_markup=color_kb(), parse_mode='Markdown')

@dp.callback_query(AkfaForm.profile_color, lambda c: c.data in ('coq','cji','cant','cbosh'))
async def p_color(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.update_data(profile_color={'coq':'Oq','cji':'Jigarrang','cant':'Antratsit','cbosh':'Boshqa'}[c.data])
    await state.set_state(AkfaForm.dimensions)
    await c.message.delete()
    await c.message.answer('📏 **Taxminiy o\'lchamlarni yozing (masalan: 120x150):**', reply_markup=back_kb(), parse_mode='Markdown')

@dp.message(AkfaForm.dimensions, lambda m: m.text and m.text.strip())
async def p_dim(m: types.Message, state: FSMContext):
    await state.update_data(dimensions=m.text.strip())
    await state.set_state(AkfaForm.quantity)
    await m.answer('📦 **Mahsulot sonini yozing (masalan: 2):**', reply_markup=back_kb(), parse_mode='Markdown')

@dp.message(AkfaForm.quantity, lambda m: m.text and m.text.strip().isdigit() and int(m.text.strip()) > 0)
async def p_qty(m: types.Message, state: FSMContext):
    await state.update_data(quantity=int(m.text.strip()))
    d = await state.get_data()
    txt = (f'📋 **Buyurtmangiz tasdiqlash uchun tayyor:**\n\n'
           f'👤 **Ism:** {d["name"]} {d["surname"]}\n'
           f'📞 **Telefon:** {d["phone"]}\n'
           f'🏗️ **Material:** {d["material"]}\n'
           f'🪟 **Oyna qavati:** {d["glass_layer"]}\n'
           f'🎨 **Oyna rangi:** {d["glass_color"]}\n'
           f'✨ **Oyna turi:** {d["glass_pattern"]}\n'
           f'🖌️ **Profil rangi:** {d["profile_color"]}\n'
           f'📏 **O\'lcham:** {d["dimensions"]}\n'
           f'📦 **Soni:** {d["quantity"]} ta\n\n'
           f'**Hammasi to\'g\'rimi?**')
    await state.set_state(AkfaForm.confirm)
    await m.answer(txt, reply_markup=confirm_kb(), parse_mode='Markdown')

# ═══════════════════════════════════════════════
# MAINTENANCE REQUEST (USTA CHAQIRISH)
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'call_master')
@dp.callback_query(F.data == 'np') # Eskisini ham qo'llab-quvvatlaymiz
async def c_master(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(MaintenanceForm.problem)
    await c.message.delete()
    await c.message.answer("🛠 **Usta chaqirish (Profilaktika)**\n\nIltimos, muammoni qisqacha yozib yuboring (masalan: o'ynak qisilib qoldi):", 
                         reply_markup=back_kb(), parse_mode='Markdown')

@dp.message(MaintenanceForm.problem, F.text)
async def p_problem(m: types.Message, state: FSMContext):
    if m.text == BACK: return
    await save_maintenance_request(m.from_user.id, m.from_user.full_name, 'Kontakt bazada', m.text.strip())
    await state.clear()
    await m.answer("✅ **Sizning so'rovingiz qabul qilindi.**\nMutaxassislarimiz tez orada bog'lanishadi.", 
                 reply_markup=ReplyKeyboardRemove())
    await m.answer("Boshqa xizmat kerakmi?", reply_markup=main_kb())

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'cy')
async def p_yes(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    d = await state.get_data()
    # Ma'lumotlarni birlashtirish (Yangi maydonlarni qo'shib)
    info_text = (f"Material: {d['material']}, Oyna: {d['glass_layer']}, "
                 f"Oyna Rangi: {d['glass_color']}, Turi: {d['glass_pattern']}, "
                 f"Profil: {d['profile_color']}")
    
    oid = await save_akfa_order(c.from_user.id, d.get('name',''), d.get('surname',''), d.get('phone',''),
                          info_text, d.get('dimensions',''), d.get('quantity',1))
    await state.clear()
    await c.message.edit_text(
        f'✅ **Buyurtmangiz qabul qilindi. ID: {oid}**\n\n'
        f'👤 **Mijoz:** {d["name"]} {d["surname"]}\n'
        f'📞 **Telefon:** {d["phone"]}\n'
        f'📐 **O\'lcham:** {d["dimensions"]}\n'
        f'📦 **Soni:** {d["quantity"]} ta\n\n'
        f'Mutaxassisimiz tez orada siz bilan bog\'lanadi.',
        reply_markup=main_kb(), parse_mode='Markdown')

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'cr')
async def p_no(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.clear()
    await state.set_state(AkfaForm.name)
    await c.message.edit_text('Buyurtma berish uchun savollarga javob bering.\n\n1/9: Ismingizni kiriting:', reply_markup=back_kb())

# ═══════════════════════════════════════════════
# ID CHECK
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'check_order')
async def chk(c: types.CallbackQuery, state: FSMContext):
    try:
        await c.answer()
        await c.message.edit_text('Buyurtmangizni tekshirish uchun 5 xonali ID raqamingizni kiriting:', reply_markup=back_kb())
        await state.set_state('chk')
    except Exception as e:
        logger.error(f"Error in check_order: {e}")

@dp.message(StateFilter('chk'))
async def chk_id(m: types.Message, state: FSMContext):
    oid = m.text.strip()
    if not oid.isdigit() or len(oid) != 5:
        await m.answer('Iltimos, to\'g\'ri 5 xonali ID kiriting (masalan: 54921):', reply_markup=back_kb()); return
    o = await get_akfa_order(oid)
    if not o:
        await m.answer('❌ Bunday ID topilmadi.', reply_markup=main_kb()); await state.clear(); return
    sm = {'pending':'⏳ Kutilmoqda','material_delivered':'🚚 Material olib kelindi','assembling':'🔧 Yig\'ilmoqda','cutting':'🪟 Oyna kesilmoqda','ready':'📦 Tayyor va yetkazilmoqda'}
    await m.answer(
        f'🔍 Buyurtma ID: {o["order_id"]}\n\n'
        f'👤 Ism: {o["name"]} {o["surname"]}\n📞 Telefon: {o["phone"]}\n'
        f'🛠 Material: {o["material"]}\n🪟 Oyna qavati: {o["glass_layer"]}\n'
        f'🎨 Rang: {o["profile_color"]}\n📐 O\'lcham: {o["dimensions"]}\n'
        f'📦 Soni: {o["quantity"]} ta\n📊 Holati: {sm.get(o["status"],o["status"])}\n'
        f'📅 Yaratilgan: {o["created_at"]}', reply_markup=main_kb())
    await state.clear()

# ═══════════════════════════════════════════════
# BOT START
# ═══════════════════════════════════════════════

async def run_bot_polling():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info('===> Bot professional rejimda (Polling) ishlamoqda...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot_polling())
    except KeyboardInterrupt:
        pass
