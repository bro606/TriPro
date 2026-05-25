# TriPro Telegram Bot - Aiogram 3.x
# FSM: AKFA buyurtmasi (9 bosqich) + Profilaktika (2 bosqich)
# Ma'lumotlar bazasi: backend.py orqali SQLite

import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from backend import save_akfa_order, get_akfa_order, save_profilaktika

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    BOT_TOKEN = '8745687733:AAFmfV5n6f0Z0RxJ70aXVf82zNa0LI3KUs4'
BOT_TOKEN = BOT_TOKEN.strip()

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Username')
SITE_URL = 'https://tripro-uz.netlify.app'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─── FSM STATES ───
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

BACK_BTN = '🔙 Bosh menyuga'

# ─── KEYBOARDS ───
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 Saytni ko\'rish', url=SITE_URL)],
        [InlineKeyboardButton(text='🪟 AKFA buyurtmasi', callback_data='new_order')],
        [InlineKeyboardButton(text='🔍 ID tekshirish', callback_data='check_order')],
        [InlineKeyboardButton(text='🛠 Boshqa xizmatlar', callback_data='other_services')],
    ])

def back_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def phone_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Kontaktni ulash', request_contact=True)],
            [KeyboardButton(text='⌨️ Raqamni yozish')],
            [KeyboardButton(text=BACK_BTN)],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def material_ikb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Plastik', callback_data='mat_plastik')],
        [InlineKeyboardButton(text='Alyumin', callback_data='mat_alyumin')],
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def glass_layer_ikb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='1 qavatli', callback_data='glass_1')],
        [InlineKeyboardButton(text='2 qavatli', callback_data='glass_2')],
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def profile_color_ikb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Oq', callback_data='color_oq')],
        [InlineKeyboardButton(text='Jigarrang', callback_data='color_jigarrang')],
        [InlineKeyboardButton(text='Antratsit', callback_data='color_antratsit')],
        [InlineKeyboardButton(text='Boshqa', callback_data='color_boshqa')],
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def confirm_ikb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Tasdiqlash', callback_data='confirm_yes')],
        [InlineKeyboardButton(text='❌ Qaytadan to\'ldirish', callback_data='confirm_retry')],
    ])

def other_services_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👨‍💻 Admin bilan bog\'lanish', url=f'https://t.me/{ADMIN_USERNAME}')],
        [InlineKeyboardButton(text='🛡 Profilaktikaga yozilish', callback_data='new_profilaktika')],
        [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='back_to_menu')],
    ])

def profilaktika_location_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📍 Joylashuvni yuborish', request_location=True)],
            [KeyboardButton(text='✏️ Manzilni yozish')],
            [KeyboardButton(text=BACK_BTN)],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def time_slots_ikb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='09:00 - 11:00', callback_data='time_0900')],
        [InlineKeyboardButton(text='11:00 - 13:00', callback_data='time_1100')],
        [InlineKeyboardButton(text='14:00 - 16:00', callback_data='time_1400')],
        [InlineKeyboardButton(text='16:00 - 18:00', callback_data='time_1600')],
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def profilaktika_offer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛡 Profilaktikaga yozilish', callback_data='new_profilaktika')],
        [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='back_to_menu')],
    ])

# ─── START / CANCEL ───
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    name = message.from_user.first_name or 'Foydalanuvchi'
    await message.answer(
        f'Assalomu alaykum, {name}! TriPro ustaxonasiga xush kelibsiz. '
        f'Biz sizga sifatli AKFA romlar, yog\'och va shisha mahsulotlarini yetkazib beramiz.',
        reply_markup=main_menu_kb()
    )

@dp.message(Command('cancel'))
@dp.message(Command('bosh_menu'))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Asosiy menyu:', reply_markup=main_menu_kb())

# ─── MENU CALLBACKS ───
@dp.callback_query(lambda c: c.data == 'back_to_menu')
async def cb_back_to_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text('Asosiy menyu:', reply_markup=main_menu_kb())

@dp.callback_query(lambda c: c.data == 'new_order')
async def cb_new_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(AkfaForm.name)
    await call.message.edit_text(
        'Buyurtma berish uchun quyidagi savollarga javob bering.\n\n1/9: Ismingizni kiriting:',
        reply_markup=back_inline_kb()
    )

@dp.callback_query(lambda c: c.data == 'other_services')
async def cb_other_services(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(
        '🛠 Yog\'och mahsulotlari va shisha xizmatlari\n\n'
        'Siz tanlagan yo\'nalish bo\'yicha buyurtmalar individual tartibda qabul qilinadi. '
        'Aniq narxlar va dizayn masalalari bo\'yicha bizning bosh mutaxassisimiz bilan '
        'bevosita bog\'laning.\n\n'
        'Shuningdek, yilda bir marta profilaktika xizmatimizdan foydalanishingiz mumkin.',
        reply_markup=other_services_kb()
    )

# ─── AKFA: 1/9 ISM ───
@dp.message(AkfaForm.name, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AkfaForm.surname)
    await message.answer('2/9: Familiyangizni kiriting:', reply_markup=back_inline_kb())

@dp.message(AkfaForm.name)
async def process_name_invalid(message: types.Message):
    await message.answer('Iltimos, ismingizni yozing:', reply_markup=back_inline_kb())

# ─── AKFA: 2/9 FAMILIYA ───
@dp.message(AkfaForm.surname, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text.strip())
    await state.set_state(AkfaForm.phone)
    await message.answer(
        '3/9: Telefon raqamingizni yuboring.\n\n'
        '"📱 Kontaktni ulash" tugmasini bosing yoki '
        '"⌨️ Raqamni yozish" ni tanlang:',
        reply_markup=phone_choice_kb()
    )

@dp.message(AkfaForm.surname)
async def process_surname_invalid(message: types.Message):
    await message.answer('Iltimos, familiyangizni yozing:', reply_markup=back_inline_kb())

# ─── AKFA: 3/9 TELEFON ───
@dp.message(AkfaForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(AkfaForm.material)
    await message.answer('4/9: Buyurtmangiz uchun material turini tanlang:', reply_markup=material_ikb())

@dp.message(AkfaForm.phone, F.text == '⌨️ Raqamni yozish')
async def process_phone_manual_choice(message: types.Message, state: FSMContext):
    await message.answer(
        'Iltimos, telefon raqamingizni kiriting (masalan: +998901234567):',
        reply_markup=back_inline_kb()
    )

@dp.message(AkfaForm.phone, lambda msg: msg.text and len(msg.text.strip()) > 5 and msg.text.strip() != BACK_BTN)
async def process_phone_text(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(AkfaForm.material)
    await message.answer('4/9: Buyurtmangiz uchun material turini tanlang:', reply_markup=material_ikb())

@dp.message(AkfaForm.phone, F.text == BACK_BTN)
async def process_phone_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Asosiy menyu:', reply_markup=main_menu_kb())

@dp.message(AkfaForm.phone)
async def process_phone_invalid(message: types.Message):
    await message.answer(
        'Iltimos, kontakt tugmasini bosing yoki raqamingizni yozing:',
        reply_markup=phone_choice_kb()
    )

# ─── AKFA: 4/9 MATERIAL ───
@dp.callback_query(AkfaForm.material, lambda c: c.data.startswith('mat_'))
async def cb_material(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    vals = {'mat_plastik': 'Plastik', 'mat_alyumin': 'Alyumin'}
    await state.update_data(material=vals[call.data])
    await state.set_state(AkfaForm.glass_layer)
    await call.message.edit_text('5/9: Oyna qavatini tanlang:', reply_markup=glass_layer_ikb())

# ─── AKFA: 5/9 OYNA QAVATI ───
@dp.callback_query(AkfaForm.glass_layer, lambda c: c.data.startswith('glass_'))
async def cb_glass_layer(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    vals = {'glass_1': '1 qavatli', 'glass_2': '2 qavatli'}
    await state.update_data(glass_layer=vals[call.data])
    await state.set_state(AkfaForm.profile_color)
    await call.message.edit_text('6/9: Profil rangini tanlang:', reply_markup=profile_color_ikb())

# ─── AKFA: 6/9 PROFIL RANGI ───
@dp.callback_query(AkfaForm.profile_color, lambda c: c.data.startswith('color_'))
async def cb_profile_color(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    vals = {'color_oq': 'Oq', 'color_jigarrang': 'Jigarrang', 'color_antratsit': 'Antratsit', 'color_boshqa': 'Boshqa'}
    await state.update_data(profile_color=vals[call.data])
    await state.set_state(AkfaForm.dimensions)
    await call.message.delete()
    await call.message.answer(
        '7/9: Taxminiy o\'lchamlarni yozing (masalan: 80x90):',
        reply_markup=back_inline_kb()
    )

# ─── AKFA: 7/9 O'LCHAM ───
@dp.message(AkfaForm.dimensions, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_dimensions(message: types.Message, state: FSMContext):
    await state.update_data(dimensions=message.text.strip())
    await state.set_state(AkfaForm.quantity)
    await message.answer('8/9: Mahsulot sonini yozing (masalan: 2):', reply_markup=back_inline_kb())

@dp.message(AkfaForm.dimensions)
async def process_dimensions_invalid(message: types.Message):
    await message.answer('Iltimos, o\'lchamlarni yozing (masalan: 80x90):', reply_markup=back_inline_kb())

# ─── AKFA: 8/9 SONI ───
@dp.message(AkfaForm.quantity, lambda msg: msg.text and msg.text.strip().isdigit() and int(msg.text.strip()) > 0)
async def process_quantity(message: types.Message, state: FSMContext):
    qty = int(message.text.strip())
    await state.update_data(quantity=qty)
    data = await state.get_data()
    text = (
        '📋 Buyurtmangiz tasdiqlash uchun tayyor:\n\n'
        f'👤 Ism: {data["name"]} {data["surname"]}\n'
        f'📞 Telefon: {data["phone"]}\n'
        f'🛠 Material: {data["material"]}\n'
        f'🪟 Oyna qavati: {data["glass_layer"]}\n'
        f'🎨 Rang: {data["profile_color"]}\n'
        f'📐 O\'lcham: {data["dimensions"]}\n'
        f'📦 Soni: {data["quantity"]} ta\n\n'
        'Hammasi to\'g\'rimi?'
    )
    await state.set_state(AkfaForm.confirm)
    await message.answer(text, reply_markup=confirm_ikb())

@dp.message(AkfaForm.quantity)
async def process_quantity_invalid(message: types.Message):
    await message.answer('Iltimos, musbat son kiriting (masalan: 2):', reply_markup=back_inline_kb())

# ─── AKFA: 9/9 TASDIQLASH ───
@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'confirm_yes')
async def cb_confirm_yes(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    order_id = save_akfa_order(
        telegram_id=call.from_user.id,
        name=data.get('name', ''),
        surname=data.get('surname', ''),
        phone=data.get('phone', ''),
        material=data.get('material', ''),
        glass_layer=data.get('glass_layer', ''),
        profile_color=data.get('profile_color', ''),
        dimensions=data.get('dimensions', ''),
        quantity=data.get('quantity', 1),
    )
    await state.clear()
    await call.message.edit_text(
        f'✅ Buyurtmangiz qabul qilindi. ID: {order_id}\n\n'
        f'📋 Buyurtma ma\'lumotlari:\n'
        f'👤 Ism: {data["name"]} {data["surname"]}\n'
        f'📞 Telefon: {data["phone"]}\n'
        f'🛠 Material: {data["material"]}\n'
        f'🪟 Oyna qavati: {data["glass_layer"]}\n'
        f'🎨 Rang: {data["profile_color"]}\n'
        f'📐 O\'lcham: {data["dimensions"]}\n'
        f'📦 Soni: {data["quantity"]} ta\n\n'
        'Mutaxassisimiz tez orada siz bilan bog\'lanadi.',
        reply_markup=main_menu_kb()
    )
    await call.message.answer(
        '🛡 Yilda bir marta profilaktika xizmatimizdan foydalaning!\n'
        'Deraza va romlaringizni tekshirib, xizmat ko\'rsatamiz.',
        reply_markup=profilaktika_offer_kb()
    )

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'confirm_retry')
async def cb_confirm_retry(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(AkfaForm.name)
    await call.message.edit_text(
        'Buyurtma berish uchun quyidagi savollarga javob bering.\n\n1/9: Ismingizni kiriting:',
        reply_markup=back_inline_kb()
    )

# ─── ID TEKSHIRISH ───
@dp.callback_query(lambda c: c.data == 'check_order')
async def cb_check_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(
        'Buyurtmangizni tekshirish uchun 5 xonali ID raqamingizni kiriting:',
        reply_markup=back_inline_kb()
    )
    await state.set_state('check_order_input')

@dp.message(StateFilter('check_order_input'))
async def process_check_order(message: types.Message, state: FSMContext):
    oid = message.text.strip()
    if not oid.isdigit() or len(oid) != 5:
        await message.answer(
            'Iltimos, to\'g\'ri 5 xonali ID raqamini kiriting (masalan: 54921):',
            reply_markup=back_inline_kb()
        )
        return
    order = get_akfa_order(oid)
    if not order:
        await message.answer('❌ Bunday ID raqamli buyurtma topilmadi.', reply_markup=main_menu_kb())
        await state.clear()
        return
    status_map = {
        'pending': '⏳ Kutilmoqda',
        'material_delivered': '🚚 Material olib kelindi',
        'assembling': '🔧 Yig\'ilmoqda',
        'cutting': '🪟 Oyna kesilmoqda',
        'ready': '📦 Tayyor va yetkazilmoqda',
    }
    text = (
        f'🔍 Buyurtma ID: {order["order_id"]}\n\n'
        f'👤 Ism: {order["name"]} {order["surname"]}\n'
        f'📞 Telefon: {order["phone"]}\n'
        f'🛠 Material: {order["material"]}\n'
        f'🪟 Oyna qavati: {order["glass_layer"]}\n'
        f'🎨 Rang: {order["profile_color"]}\n'
        f'📐 O\'lcham: {order["dimensions"]}\n'
        f'📦 Soni: {order["quantity"]} ta\n'
        f'📊 Holati: {status_map.get(order["status"], order["status"])}\n'
        f'📅 Yaratilgan: {order["created_at"]}'
    )
    await message.answer(text, reply_markup=main_menu_kb())
    await state.clear()

# ─── PROFILAKTIKA: BOSHLASH ───
@dp.callback_query(lambda c: c.data == 'new_profilaktika')
async def cb_new_profilaktika(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(ProfilaktikaForm.location)
    await call.message.edit_text(
        '🛡 Profilaktika xizmati\n\n'
        'Manzilingizni yuboring yoki yozing (masalan: Farg\'ona sh., Navoiy ko\'ch. 15):',
        reply_markup=profilaktika_location_kb()
    )

# ─── PROFILAKTIKA: MANZIL ───
@dp.message(ProfilaktikaForm.location, F.location)
async def process_profilaktika_location_shared(message: types.Message, state: FSMContext):
    loc = message.location
    await state.update_data(location=f'{loc.latitude}, {loc.longitude}')
    await state.set_state(ProfilaktikaForm.time)
    await message.answer('Qulay vaqtni tanlang:', reply_markup=time_slots_ikb())

@dp.message(ProfilaktikaForm.location, F.text == '✏️ Manzilni yozish')
async def process_profilaktika_location_manual_choice(message: types.Message, state: FSMContext):
    await message.answer(
        'Iltimos, manzilingizni yozing (masalan: Farg\'ona sh., Navoiy ko\'ch. 15):',
        reply_markup=back_inline_kb()
    )

@dp.message(ProfilaktikaForm.location, lambda msg: msg.text and len(msg.text.strip()) > 3 and msg.text.strip() != BACK_BTN)
async def process_profilaktika_location_text(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text.strip())
    await state.set_state(ProfilaktikaForm.time)
    await message.answer('Qulay vaqtni tanlang:', reply_markup=time_slots_ikb())

@dp.message(ProfilaktikaForm.location, F.text == BACK_BTN)
async def process_profilaktika_location_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Asosiy menyu:', reply_markup=main_menu_kb())

@dp.message(ProfilaktikaForm.location)
async def process_profilaktika_location_invalid(message: types.Message):
    await message.answer(
        'Iltimos, joylashuv yuboring yoki manzilni yozing:',
        reply_markup=profilaktika_location_kb()
    )

# ─── PROFILAKTIKA: VAQT ───
@dp.callback_query(ProfilaktikaForm.time, lambda c: c.data.startswith('time_'))
async def cb_profilaktika_time(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    time_map = {
        'time_0900': '09:00 - 11:00',
        'time_1100': '11:00 - 13:00',
        'time_1400': '14:00 - 16:00',
        'time_1600': '16:00 - 18:00',
    }
    time_slot = time_map[call.data]
    data = await state.get_data()
    user = call.from_user
    save_profilaktika(
        telegram_id=user.id,
        name=user.first_name or '',
        surname=user.last_name or '',
        phone='',
        location=data.get('location', 'Noma\'lum'),
        time_slot=time_slot,
    )
    await state.clear()
    await call.message.edit_text(
        f'✅ Profilaktika xizmatiga yozildingiz!\n\n'
        f'📍 Manzil: {data["location"]}\n'
        f'⏰ Vaqt: {time_slot}\n\n'
        'Mutaxassisimiz belgilangan vaqtda siz bilan bog\'lanadi.',
        reply_markup=main_menu_kb()
    )

@dp.callback_query(ProfilaktikaForm.time, lambda c: c.data == 'back_to_menu')
async def cb_profilaktika_time_back(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text('Asosiy menyu:', reply_markup=main_menu_kb())

# ─── BOTNI ISHGA TUSHIRISH ───
async def bot_main(start_web_server=False):
    if start_web_server:
        pass
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info('Bot started polling...')
    await dp.start_polling(bot)
