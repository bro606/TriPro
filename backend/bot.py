import asyncio, os, random, logging
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ErrorEvent
from aiogram.fsm.storage.memory import MemoryStorage

# Yangi database modulidan import
try:
    from .database import (
        init_db, save_akfa_order, get_akfa_order, save_maintenance_request, 
        save_user, get_orders_for_maintenance
    )
except ImportError:
    from database import (
        init_db, save_akfa_order, get_akfa_order, save_maintenance_request, 
        save_user, get_orders_for_maintenance
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'TriPro_Admin')
SITE_URL = 'https://tripro.vercel.app'
BASE_DIR = Path(__file__).parent.parent
LOCAL_DB = str(BASE_DIR / 'tripro.db')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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

# ═══════════════════════════════════════════════
# INLINE KEYBOARDS (PROFESSIONAL DIZAYN)
# ═══════════════════════════════════════════════

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 Saytni ko\'rish', url=SITE_URL)],
        [InlineKeyboardButton(text='🚪 AKFA buyurtmasi', callback_data='start_order')],
        [InlineKeyboardButton(text='🔍 ID tekshirish', callback_data='check_id')],
        [InlineKeyboardButton(text='🛠 Texnik xizmat', callback_data='start_maintenance')],
        [InlineKeyboardButton(text='⚙️ Boshqa xizmatlar', callback_data='other_services')]
    ])

def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def phone_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📞  Telefon raqamni yozish', callback_data='phone_manual')],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def mat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🏗  Plastik', callback_data='mat_Plastik'),
            InlineKeyboardButton(text='🪟  Alyumin', callback_data='mat_Alyumin'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def glass_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='1️⃣  Bir qavatli', callback_data='glass_1 qavatli'),
            InlineKeyboardButton(text='2️⃣  Ikki qavatli', callback_data='glass_2 qavatli'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def glass_color_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='⚪  Shaffof', callback_data='gcol_Shaffof'),
            InlineKeyboardButton(text='🩶  Kulrang', callback_data='gcol_Kulrang'),
            InlineKeyboardButton(text='🟤  Bronza', callback_data='gcol_Bronza'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def glass_pattern_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✨  Naqshli (Gulli)', callback_data='gpat_Gulli'),
            InlineKeyboardButton(text='🔲  Oddiy (Silliq)', callback_data='gpat_Oddiy'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def color_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='⚪  Oq', callback_data='pcol_Oq'),
            InlineKeyboardButton(text='🟤  Jigarrang', callback_data='pcol_Jigarrang'),
        ],
        [
            InlineKeyboardButton(text='⚫  Antratsit', callback_data='pcol_Antratsit'),
            InlineKeyboardButton(text='🎨  Boshqa rang', callback_data='pcol_Boshqa'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅  Tasdiqlash', callback_data='confirm_yes'),
            InlineKeyboardButton(text='🔄  Qaytadan', callback_data='confirm_no'),
        ],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def other_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👨‍💻  Admin bilan bog\'lanish', url=f'https://t.me/{ADMIN_USERNAME}')],
        [InlineKeyboardButton(text='🛡  Profilaktikaga yozilish', callback_data='np')],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def offer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛡  Profilaktikaga yozilish', callback_data='np')],
        [InlineKeyboardButton(text='🏠  Bosh menyuga qaytish', callback_data='to_menu')]
    ])

def maintenance_reminder_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛠  Usta chaqirish', callback_data='call_master')]
    ])

# ═══════════════════════════════════════════════
# YORDAMCHI FUNKSIYA — MENYU YUBORISH
# ═══════════════════════════════════════════════

async def send_main_menu(target):
    """target: message yoki callback_query.message"""
    text = "Asosiy menyu. Quyidagi xizmatlardan birini tanlang 👇"
    await target.answer(text, reply_markup=main_kb())

# ═══════════════════════════════════════════════
# START / CANCEL
# ═══════════════════════════════════════════════

@dp.message(Command('start'))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await save_user(m.from_user.id, m.from_user.username, m.from_user.first_name, m.from_user.last_name)
    welcome_txt = (
        f"Assalomu alaykum, {m.from_user.first_name}! 👋\n\n"
        "TriPro ustaxonasiga xush kelibsiz! Uyingiz ko'rki va mustahkamligi uchun biz doim xizmatingizdamiz.\n\n"
        "Bizning asosiy bo'limlarimiz:\n"
        "🚪 AKFA bo'limi: Zamonaviy deraza va eshik tizimlari.\n"
        "🖼 Oyna bo'limi: Oyna kesish xizmatlari.\n"
        "🪵 Yog'och bo'limi: Asalarichilik uchun maxsus yog'och uyalar.\n\n"
        "✅ Kafolat: Biz bajargan barcha ishlarimizga 1 oylik rasmiy kafolat taqdim etamiz!\n\n"
        "TriPro Mini App'imizga kiring, barcha xizmatlarimiz va namunalarimiz bilan yaqindan tanishing! 👇"
    )
    await m.answer(welcome_txt, reply_markup=main_kb())

@dp.message(Command('cancel'))
async def cancel_cmd(m: types.Message, state: FSMContext):
    await state.clear()
    await send_main_menu(m)

@dp.callback_query(F.data == 'to_menu')
async def to_menu(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    await send_main_menu(c.message)

# ═══════════════════════════════════════════════
# ASOSIY MENYU TUGMALARI (CALLBACK)
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'start_order')
async def cb_start_order(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(AkfaForm.name)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 1/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤  Ismingizni kiriting:\n\n"
        "_Masalan: Jasur_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'check_id')
async def cb_check_id(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state('chk')
    await c.message.answer(
        "🔍  *Buyurtma Tekshirish*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝  5 xonali buyurtma ID raqamingizni yozing:\n\n"
        "_Masalan: 54921_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'start_maintenance')
async def cb_start_maintenance(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(MaintenanceForm.problem)
    await c.message.answer(
        "🛠  *Texnik Xizmat So'rovi*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✏️  Muammoni qisqacha yozib yuboring:\n\n"
        "_Masalan: Deraza qisilib qoldi, tutqich singan_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'other_services')
async def cb_other_services(c: types.CallbackQuery):
    await c.answer()
    await c.message.answer(
        "⚙️  *Boshqa Xizmatlar*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📦  Yog'och mahsulotlari va shisha xizmatlari\n\n"
        "Ushbu yo'nalish bo'yicha buyurtmalar individual tartibda "
        "qabul qilinadi. Aniq narxlar va dizayn masalalari bo'yicha "
        "mutaxassisimiz bilan to'g'ridan-to'g'ri bog'laning.\n\n"
        "🛡  Shuningdek, yilda bir marta *bepul profilaktika* "
        "xizmatimizdan foydalanishingiz mumkin!",
        reply_markup=other_kb(),
        parse_mode='Markdown'
    )

# ═══════════════════════════════════════════════
# AKFA FSM — FORM STEPS
# ═══════════════════════════════════════════════

@dp.message(AkfaForm.name, lambda m: m.text and m.text.strip())
async def p_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(AkfaForm.surname)
    await m.answer(
        "📋  *Yangi Buyurtma — 2/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Ism: *{m.text.strip()}*\n\n"
        "👤  Familiyangizni kiriting:\n\n"
        "_Masalan: Toshmatov_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.message(AkfaForm.surname, lambda m: m.text and m.text.strip())
async def p_surname(m: types.Message, state: FSMContext):
    await state.update_data(surname=m.text.strip())
    await state.set_state(AkfaForm.phone)
    await m.answer(
        "📋  *Yangi Buyurtma — 3/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Familiya: *{m.text.strip()}*\n\n"
        "📱  Telefon raqamingizni yozing:\n\n"
        "_Masalan: +998901234567_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'phone_manual')
async def cb_phone_manual(c: types.CallbackQuery):
    await c.answer("Raqamingizni yozing 👆", show_alert=False)

@dp.message(AkfaForm.phone, F.contact)
async def p_ph_contact(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number)
    await state.set_state(AkfaForm.material)
    await m.answer(
        "📋  *Yangi Buyurtma — 4/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Telefon: *{m.contact.phone_number}*\n\n"
        "🏗  Material turini tanlang:",
        reply_markup=mat_kb(),
        parse_mode='Markdown'
    )

@dp.message(AkfaForm.phone, lambda m: m.text and len(m.text.strip()) > 5)
async def p_ph_text(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text.strip())
    await state.set_state(AkfaForm.material)
    await m.answer(
        "📋  *Yangi Buyurtma — 4/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Telefon: *{m.text.strip()}*\n\n"
        "🏗  Material turini tanlang:",
        reply_markup=mat_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.material, F.data.startswith('mat_'))
async def p_mat(c: types.CallbackQuery, state: FSMContext):
    mat_type = c.data.replace('mat_', '')
    await c.answer(f"✅ {mat_type} tanlandi")
    await state.update_data(material=mat_type)
    await state.set_state(AkfaForm.glass_layer)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 5/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Material: *{mat_type}*\n\n"
        "🪟  Oyna qavatini tanlang:",
        reply_markup=glass_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.glass_layer, F.data.startswith('glass_'))
async def p_glass(c: types.CallbackQuery, state: FSMContext):
    layer = c.data.replace('glass_', '')
    await c.answer(f"✅ {layer} tanlandi")
    await state.update_data(glass_layer=layer)
    await state.set_state(AkfaForm.glass_color)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 6/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Oyna qavati: *{layer}*\n\n"
        "🎨  Oyna rangini tanlang:",
        reply_markup=glass_color_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.glass_color, F.data.startswith('gcol_'))
async def p_glass_color(c: types.CallbackQuery, state: FSMContext):
    color_name = c.data.replace('gcol_', '')
    await c.answer(f"✅ {color_name} tanlandi")
    await state.update_data(glass_color=color_name)
    await state.set_state(AkfaForm.glass_pattern)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 7/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Oyna rangi: *{color_name}*\n\n"
        "✨  Oyna ko'rinishini tanlang:",
        reply_markup=glass_pattern_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.glass_pattern, F.data.startswith('gpat_'))
async def p_glass_pattern(c: types.CallbackQuery, state: FSMContext):
    pattern_name = c.data.replace('gpat_', '')
    await c.answer(f"✅ {pattern_name} tanlandi")
    await state.update_data(glass_pattern=pattern_name)
    await state.set_state(AkfaForm.profile_color)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 8/9*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Oyna turi: *{pattern_name}*\n\n"
        "🖌️  Profil (rama) rangini tanlang:",
        reply_markup=color_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.profile_color, F.data.startswith('pcol_'))
async def p_color(c: types.CallbackQuery, state: FSMContext):
    color_p = c.data.replace('pcol_', '')
    await c.answer(f"✅ {color_p} tanlandi")
    await state.update_data(profile_color=color_p)
    await state.set_state(AkfaForm.dimensions)
    await c.message.answer(
        "📋  *Yangi Buyurtma — 9/9 (a)*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  Profil rangi: *{color_p}*\n\n"
        "📐  Taxminiy o'lchamlarni yozing:\n\n"
        "_Ko'rinish: Kenglik × Balandlik (sm)\n"
        "Masalan: 120×150_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.message(AkfaForm.dimensions, lambda m: m.text and m.text.strip())
async def p_dim(m: types.Message, state: FSMContext):
    await state.update_data(dimensions=m.text.strip())
    await state.set_state(AkfaForm.quantity)
    await m.answer(
        "📋  *Yangi Buyurtma — 9/9 (b)*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅  O'lcham: *{m.text.strip()}*\n\n"
        "📦  Nechta buyurtma berasiz?\n\n"
        "_Masalan: 2_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.message(AkfaForm.quantity, lambda m: m.text and m.text.strip().isdigit() and int(m.text.strip()) > 0)
async def p_qty(m: types.Message, state: FSMContext):
    await state.update_data(quantity=int(m.text.strip()))
    d = await state.get_data()
    txt = (
        "📋  *Buyurtma Tasdiqlash*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌  *Tanlangan ma'lumotlar:*\n\n"
        f"👤  Ism Familiya: *{d['name']} {d['surname']}*\n"
        f"📞  Telefon: *{d['phone']}*\n"
        f"🏗️  Material: *{d['material']}*\n"
        f"🪟  Oyna qavati: *{d['glass_layer']}*\n"
        f"🎨  Oyna rangi: *{d['glass_color']}*\n"
        f"✨  Oyna turi: *{d['glass_pattern']}*\n"
        f"🖌️  Profil rangi: *{d['profile_color']}*\n"
        f"📐  O'lcham: *{d['dimensions']}*\n"
        f"📦  Soni: *{d['quantity']} ta*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅  Hammasi to'g'rimi?"
    )
    await state.set_state(AkfaForm.confirm)
    await m.answer(txt, reply_markup=confirm_kb(), parse_mode='Markdown')

# ═══════════════════════════════════════════════
# TASDIQLASH
# ═══════════════════════════════════════════════

@dp.callback_query(AkfaForm.confirm, F.data == 'confirm_yes')
async def p_yes(c: types.CallbackQuery, state: FSMContext):
    await c.answer("⏳ Saqlanmoqda...")
    d = await state.get_data()
    info_text = (f"Material: {d['material']}, Oyna: {d['glass_layer']}, "
                 f"Oyna Rangi: {d['glass_color']}, Turi: {d['glass_pattern']}, "
                 f"Profil: {d['profile_color']}")
    oid = await save_akfa_order(c.from_user.id, d.get('name',''), d.get('surname',''), d.get('phone',''),
                          info_text, d.get('dimensions',''), d.get('quantity',1))
    await state.clear()
    await c.message.answer(
        "🎉  *Buyurtmangiz muvaffaqiyatli qabul qilindi!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  Mijoz: *{d['name']} {d['surname']}*\n"
        f"📞  Telefon: *{d['phone']}*\n"
        f"📐  O'lcham: *{d['dimensions']}*\n"
        f"📦  Soni: *{d['quantity']} ta*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏰  Buyurtmangiz qabul qilindi. Tez orada mutaxassisimiz siz bilan bog'lanib to'lov tafsilotlarini tushuntiradi.\n"
        "💳  To'lov amalga oshirilgandan so'ng, sizga buyurtma ID raqami yuboriladi va u orqali buyurtma holatini tekshirishingiz mumkin bo'ladi!",
        reply_markup=offer_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(AkfaForm.confirm, F.data == 'confirm_no')
async def p_no(c: types.CallbackQuery, state: FSMContext):
    await c.answer("🔄 Qaytadan boshlanmoqda...")
    await state.clear()
    await state.set_state(AkfaForm.name)
    await c.message.answer(
        "🔄  *Buyurtma qaytadan boshlanmoqda...*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📋  *Yangi Buyurtma — 1/9*\n\n"
        "👤  Ismingizni kiriting:\n\n"
        "_Masalan: Jasur_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

# ═══════════════════════════════════════════════
# MAINTENANCE REQUEST (USTA CHAQIRISH)
# ═══════════════════════════════════════════════

@dp.callback_query(F.data == 'np')
async def c_master(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(MaintenanceForm.problem)
    await c.message.answer(
        "🛠  *Texnik Xizmat So'rovi*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✏️  Muammoni qisqacha yozib yuboring:\n\n"
        "_Masalan: Deraza qisilib qoldi, tutqich singan_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.callback_query(F.data == 'call_master')
async def cb_call_master(c: types.CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(MaintenanceForm.problem)
    await c.message.answer(
        "🛠  *Usta Chaqirish*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✏️  Muammoni qisqacha yozib yuboring:\n\n"
        "_Masalan: Deraza qisilib qoldi, tutqich singan_",
        reply_markup=cancel_kb(),
        parse_mode='Markdown'
    )

@dp.message(MaintenanceForm.problem, F.text)
async def p_problem(m: types.Message, state: FSMContext):
    await save_maintenance_request(m.from_user.id, m.from_user.full_name, 'Kontakt bazada', m.text.strip())
    await state.clear()
    await m.answer(
        "✅  *So'rovingiz qabul qilindi!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝  Muammo: _{m.text.strip()}_\n\n"
        "👨‍🔧  Mutaxassislarimiz *tez orada* siz bilan bog'lanishadi.\n\n"
        "⏰  Ish vaqti: 09:00 — 18:00",
        reply_markup=main_kb(),
        parse_mode='Markdown'
    )

# ═══════════════════════════════════════════════
# ID CHECK
# ═══════════════════════════════════════════════

@dp.message(StateFilter('chk'))
async def chk_id(m: types.Message, state: FSMContext):
    oid = m.text.strip()
    if not oid.isdigit() or len(oid) != 5:
        await m.answer(
            "⚠️  *Noto'g'ri format!*\n\n"
            "📝  Iltimos, to'g'ri 5 xonali ID kiriting.\n\n"
            "_Masalan: 54921_",
            reply_markup=cancel_kb(),
            parse_mode='Markdown'
        )
        return
    o = await get_akfa_order(oid)
    if not o:
        await m.answer(
            "❌  *Buyurtma topilmadi!*\n\n"
            f"🔍  ID: *{oid}* bo'yicha hech qanday buyurtma mavjud emas.\n\n"
            "_ID raqamni tekshirib qaytadan urinib ko'ring._",
            reply_markup=main_kb(),
            parse_mode='Markdown'
        )
        await state.clear()
        return
    sm = {
        'pending':            '⏳  Kutilmoqda',
        'material_delivered': '🚚  Material olib kelindi',
        'assembling':         '🔧  Yig\'ilmoqda',
        'cutting':            '🪟  Oyna kesilmoqda',
        'ready':              '📦  Tayyor va yetkazilmoqda',
    }
    status_label = sm.get(o['status'], o['status'])
    await m.answer(
        "🔍  *Buyurtma Ma'lumotlari*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔  Buyurtma ID: *#{o['order_id']}*\n\n"
        f"👤  Ism: *{o['name']} {o['surname']}*\n"
        f"📞  Telefon: *{o['phone']}*\n"
        f"🏗️  Material: *{o['material']}*\n"
        f"🪟  Oyna qavati: *{o['glass_layer']}*\n"
        f"🎨  Rang: *{o['profile_color']}*\n"
        f"📐  O'lcham: *{o['dimensions']}*\n"
        f"📦  Soni: *{o['quantity']} ta*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊  Holati: {status_label}\n"
        f"📅  Sana: {o['created_at']}",
        reply_markup=main_kb(),
        parse_mode='Markdown'
    )
    await state.clear()

# ═══════════════════════════════════════════════
# FALLBACK HANDLERS — SERVER RESTART DAN KEYIN
# Agar foydalanuvchi so'rovnoma o'rta bog'ida server
# qayta ishga tushsa, MemoryStorage o'chadi.
# Bu handler "qotib qolgan" foydalanuvchilarga
# avtomatik yordam beradi.
# ═══════════════════════════════════════════════

@dp.callback_query()
async def fallback_callback(c: types.CallbackQuery, state: FSMContext):
    """Hech bir handler ushlamagan callback — state yo'qolgan bo'lishi mumkin"""
    current_state = await state.get_state()
    logger.warning(f"Fallback callback: data={c.data}, state={current_state}, user={c.from_user.id}")
    await c.answer("⚠️ Sessiya tugadi", show_alert=False)
    await state.clear()
    await c.message.answer(
        "⏱  *Server yangilandi*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Kechirasiz, server yangilanishi sababli joriy sessiya uzildi.\n\n"
        "Iltimos, bosh menyudan qaytadan boshlang 👇",
        reply_markup=main_kb(),
        parse_mode='Markdown'
    )

@dp.message()
async def fallback_message(m: types.Message, state: FSMContext):
    """Hech bir handler ushlamagan xabar — noto'g'ri state yoki yo'qolgan state"""
    current_state = await state.get_state()
    logger.warning(f"Fallback message: text={m.text!r}, state={current_state}, user={m.from_user.id}")
    await state.clear()
    await m.answer(
        "⏱  *Server yangilandi*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Kechirasiz, server yangilanishi sababli joriy sessiya uzildi.\n\n"
        "Iltimos, bosh menyudan qaytadan boshlang 👇",
        reply_markup=main_kb(),
        parse_mode='Markdown'
    )

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
