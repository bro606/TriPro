import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, create_order, get_orders_for_chat, get_order, get_unnotified_confirmations, mark_notified

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = '8745687733:AAFf87qQlNCJdAiQcErItQ3mKsMYl6sByBM'
SITE_URL = 'https://tripro.uz'  # Replace with your actual domain

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─── FSM STATES ───
class OrderForm(StatesGroup):
    material = State()
    glass = State()
    color = State()
    dimensions = State()
    phone = State()

# ─── INLINE KEYBOARDS ───
def material_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Plastik (PVA)'), KeyboardButton(text='Alyumin')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def glass_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='1 qavatli (oddiy)'), KeyboardButton(text='2 qavatli (vakuumli)')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def color_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Oq'), KeyboardButton(text='Jigarrang')],
                  [KeyboardButton(text='Antratsit'), KeyboardButton(text='Boshqa')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='📞 Kontaktni yuborish', request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 TriPro galereyasini ko\'rish', web_app=WebAppInfo(url=SITE_URL))],
        [InlineKeyboardButton(text='📝 Buyurtma berish', callback_data='new_order')],
        [InlineKeyboardButton(text='🔍 Buyurtmani tekshirish', callback_data='check_order')],
    ])

# ─── COMMANDS ───
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        f'Assalomu alaykum, {message.from_user.first_name}! 👋\n\n'
        f'TriPro — AKFA romlar, oynak xizmatlari va yog\'och mahsulotlari ishlab chiqaruvchi '
        f'professional ustaxona.\n\n'
        f'Galereyani ko\'rib, buyurtma berishingiz yoki mavjud buyurtmangiz holatini '
        f'tekshirishingiz mumkin.',
        reply_markup=main_menu()
    )

@dp.message(Command('cancel'))
@dp.message(Command('bosh_menu'))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Bosh menyu:', reply_markup=main_menu())

# ─── CALLBACKS ───
@dp.callback_query(lambda c: c.data == 'new_order')
async def cb_new_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        'Buyurtma berish uchun bir necha savolga javob bering.\n\n'
        '1-savol: Material turini tanlang:',
        reply_markup=material_kb()
    )
    await state.set_state(OrderForm.material)

@dp.callback_query(lambda c: c.data == 'check_order')
async def cb_check_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer('Iltimos, 4 xonali buyurtma ID raqamingizni kiriting:')
    await state.set_state('check_order_input')

# ─── FSM: MATERIAL ───
@dp.message(OrderForm.material, F.text.in_(['Plastik (PVA)', 'Alyumin']))
async def process_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await message.answer('2-savol: Oyna qavatini tanlang:', reply_markup=glass_kb())
    await state.set_state(OrderForm.glass)

@dp.message(OrderForm.material)
async def process_material_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=material_kb())

# ─── FSM: GLASS ───
@dp.message(OrderForm.glass, F.text.in_(['1 qavatli (oddiy)', '2 qavatli (vakuumli)']))
async def process_glass(message: types.Message, state: FSMContext):
    await state.update_data(glass=message.text)
    await message.answer('3-savol: Profil rangini tanlang:', reply_markup=color_kb())
    await state.set_state(OrderForm.color)

@dp.message(OrderForm.glass)
async def process_glass_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=glass_kb())

# ─── FSM: COLOR ───
@dp.message(OrderForm.color, F.text.in_(['Oq', 'Jigarrang', 'Antratsit', 'Boshqa']))
async def process_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    await message.answer(
        '4-savol: Taxminiy o\'lchamlarni yozing (masalan: 1.5x2):',
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(OrderForm.dimensions)

@dp.message(OrderForm.color)
async def process_color_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=color_kb())

# ─── FSM: DIMENSIONS ───
@dp.message(OrderForm.dimensions, lambda msg: len(msg.text.strip()) > 0)
async def process_dimensions(message: types.Message, state: FSMContext):
    await state.update_data(dimensions=message.text.strip())
    await message.answer(
        '5-savol (oxirgi): Telefon raqamingizni yuboring yoki kontakt tugmasini bosing:',
        reply_markup=phone_kb()
    )
    await state.set_state(OrderForm.phone)

@dp.message(OrderForm.dimensions)
async def process_dimensions_invalid(message: types.Message):
    await message.answer('Iltimos, o\'lchamlarni yozing (masalan: 1.5x2):')

# ─── FSM: PHONE ───
@dp.message(OrderForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    data = await state.update_data(phone=phone)
    await _finish_order(message, data)
    await state.clear()

@dp.message(OrderForm.phone, lambda msg: msg.text and len(msg.text.strip()) > 5)
async def process_phone_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.update_data(phone=phone)
    await _finish_order(message, data)
    await state.clear()

@dp.message(OrderForm.phone)
async def process_phone_invalid(message: types.Message):
    await message.answer(
        'Iltimos, telefon raqamingizni yozing yoki "Kontaktni yuborish" tugmasini bosing:',
        reply_markup=phone_kb()
    )

async def _finish_order(message: types.Message, data: dict):
    order_id = create_order(
        telegram_id=message.from_user.id,
        material_type=data.get('material', 'Noma\'lum'),
        glass_type=data.get('glass', 'Noma\'lum'),
        profile_color=data.get('color', 'Noma\'lum'),
        dimensions=data.get('dimensions', 'Noma\'lum'),
        phone=data.get('phone', 'Noma\'lum')
    )
    text = (
        '✅ Buyurtmangiz qabul qilindi!\n\n'
        f'📦 Material: {data["material"]}\n'
        f'🪟 Oyna qavati: {data["glass"]}\n'
        f'🎨 Profil rangi: {data["color"]}\n'
        f'📐 O\'lchamlar: {data["dimensions"]}\n'
        f'📞 Telefon: {data["phone"]}\n\n'
        'Tez orada mutaxassisimiz siz bilan bog\'lanadi. ID raqamingiz '
        'buyurtma tasdiqlangandan so\'ng beriladi.'
    )
    await message.answer(text, reply_markup=main_menu())

# ─── CHECK ORDER BY ID ───
@dp.message(StateFilter('check_order_input'))
async def process_check_order(message: types.Message, state: FSMContext):
    oid = message.text.strip()
    if not oid.isdigit() or len(oid) != 4:
        await message.answer('Iltimos, to\'g\'ri 4 xonali ID raqamini kiriting (masalan: 3487):')
        return
    order = get_order(oid)
    if not order:
        await message.answer('❌ Bunday ID raqamli buyurtma topilmadi. Qaytadan tekshirib ko\'ring.')
        await state.clear()
        return
    status_map = {
        'pending': '⏳ Kutilmoqda',
        'confirmed': '✅ Tasdiqlangan',
        'material_delivered': '🚚 Material keltirilmoqda',
        'in_progress': '🔧 Jarayonda (Profil yig\'ish)',
        'ready': '✨ Oyna qismi tayyorlanmoqda',
        'delivered': '📦 Tayyor va Yetkazilmoqda',
    }
    text = (
        f'🔍 Buyurtma ID: {order["order_id"]}\n\n'
        f'📦 Material: {order["material_type"]}\n'
        f'🪟 Oyna qavati: {order["glass_type"]}\n'
        f'🎨 Profil rangi: {order["profile_color"]}\n'
        f'📐 O\'lchamlar: {order["dimensions"]}\n'
        f'📞 Telefon: {order["phone"]}\n'
        f'📊 Holati: {status_map.get(order["status"], order["status"])}\n'
        f'📅 Yaratilgan: {order["created_at"]}'
    )
    await message.answer(text)
    await state.clear()

# ─── BACKGROUND: NOTIFY CONFIRMED ORDERS ───
async def notify_checker():
    while True:
        try:
            confirmed = get_unnotified_confirmations()
            for order in confirmed:
                status_map = {
                    'confirmed': '✅ Tasdiqlangan',
                    'material_delivered': '🚚 Material keltirilmoqda',
                    'in_progress': '🔧 Jarayonda (Profil yig\'ish)',
                    'ready': '✨ Oyna qismi tayyorlanmoqda',
                    'delivered': '📦 Tayyor va Yetkazilmoqda',
                }
                text = (
                    f'🎉 Xushxabar!\n\n'
                    f'Sizning buyurtmangiz tasdiqlandi.\n'
                    f'🆔 ID raqamingiz: <b>{order["order_id"]}</b>\n\n'
                    f'📦 Material: {order["material_type"]}\n'
                    f'🪟 Oyna qavati: {order["glass_type"]}\n'
                    f'🎨 Profil rangi: {order["profile_color"]}\n'
                    f'📐 O\'lchamlar: {order["dimensions"]}\n'
                    f'📊 Holati: {status_map[order["status"]]}\n\n'
                    f'Buyurtmangiz holatini bot orqali kuzatib borishingiz mumkin: '
                    f'🔍 Buyurtmani tekshirish'
                )
                try:
                    await bot.send_message(order['telegram_id'], text, parse_mode='HTML')
                    mark_notified(order['order_id'])
                    logger.info(f'Notified user {order["telegram_id"]} about order {order["order_id"]}')
                except Exception as e:
                    logger.error(f'Failed to notify user {order["telegram_id"]}: {e}')
        except Exception as e:
            logger.error(f'Notify checker error: {e}')
        await asyncio.sleep(10)

# ─── MAIN ───
async def main():
    init_db()
    asyncio.create_task(notify_checker())
    logger.info('Bot started polling...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
