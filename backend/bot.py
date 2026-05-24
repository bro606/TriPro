import asyncio
import os
import sys
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, create_order, get_orders_for_chat, get_order, get_unnotified_confirmations, mark_notified, get_unnotified_deliveries, mark_delivery_notified

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
print(f"DEBUG: Token qiymati: {os.getenv('BOT_TOKEN')}")
if not BOT_TOKEN:
    print("XATO: BOT_TOKEN topilmadi! Render muhitini tekshir.")
    sys.exit(1)
SITE_URL = 'https://tripro-uz.netlify.app'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─── FSM STATES ───
class OrderForm(StatesGroup):
    material = State()
    profile_color = State()
    glass_type = State()
    glass_pattern = State()
    glass_color = State()
    dimensions = State()
    quantity_choice = State()
    quantity_number = State()
    add_more = State()
    phone = State()

# ─── INLINE KEYBOARDS ───
def material_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Plastik (PVA)'), KeyboardButton(text='Alyumin')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def profile_color_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Oq'), KeyboardButton(text='Jigarrang')],
                  [KeyboardButton(text='Antratsit'), KeyboardButton(text='Boshqa')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def glass_type_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='1 qavatli (oddiy)'), KeyboardButton(text='2 qavatli (vakuumli)')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def glass_pattern_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Gulli'), KeyboardButton(text='Oddiy')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def glass_color_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Oq'), KeyboardButton(text='Jigarrang')],
                  [KeyboardButton(text='Boshqa rang')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def quantity_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Bitta'), KeyboardButton(text='Ko\'p')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='Ha'), KeyboardButton(text='Yo\'q')]],
        resize_keyboard=True, one_time_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='📞 Kontaktni yuborish', request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 TriPro saytini ochish', web_app=WebAppInfo(url=SITE_URL))],
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
        f'Saytni ko\'rib, buyurtma berishingiz yoki mavjud buyurtmangiz holatini '
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
        '1/8: Material turini tanlang:',
        reply_markup=material_kb()
    )
    await state.set_state(OrderForm.material)

@dp.callback_query(lambda c: c.data == 'check_order')
async def cb_check_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer('Iltimos, 4 xonali buyurtma ID raqamingizni kiriting:')
    await state.set_state('check_order_input')

# ─── FSM: MATERIAL (1) ───
PROFILE_COLORS = ['Oq', 'Jigarrang', 'Antratsit', 'Boshqa']
GLASS_TYPES = ['1 qavatli (oddiy)', '2 qavatli (vakuumli)']
GLASS_PATTERNS = ['Gulli', 'Oddiy']
GLASS_COLORS = ['Oq', 'Jigarrang', 'Boshqa rang']

@dp.message(OrderForm.material, F.text.in_(['Plastik (PVA)', 'Alyumin']))
async def process_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await message.answer('2/8: Profil rangini tanlang:', reply_markup=profile_color_kb())
    await state.set_state(OrderForm.profile_color)

@dp.message(OrderForm.material)
async def process_material_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=material_kb())

# ─── FSM: PROFILE COLOR (2) ───
@dp.message(OrderForm.profile_color, F.text.in_(PROFILE_COLORS))
async def process_profile_color(message: types.Message, state: FSMContext):
    await state.update_data(profile_color=message.text)
    await message.answer('3/8: Oyna qavatini tanlang:', reply_markup=glass_type_kb())
    await state.set_state(OrderForm.glass_type)

@dp.message(OrderForm.profile_color)
async def process_profile_color_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=profile_color_kb())

# ─── FSM: GLASS TYPE (3) ───
@dp.message(OrderForm.glass_type, F.text.in_(GLASS_TYPES))
async def process_glass_type(message: types.Message, state: FSMContext):
    await state.update_data(glass_type=message.text)
    await message.answer('4/8: Oyna naqshini tanlang:', reply_markup=glass_pattern_kb())
    await state.set_state(OrderForm.glass_pattern)

@dp.message(OrderForm.glass_type)
async def process_glass_type_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=glass_type_kb())

# ─── FSM: GLASS PATTERN (4) ───
@dp.message(OrderForm.glass_pattern, F.text.in_(GLASS_PATTERNS))
async def process_glass_pattern(message: types.Message, state: FSMContext):
    await state.update_data(glass_pattern=message.text)
    await message.answer('5/8: Oyna rangini tanlang:', reply_markup=glass_color_kb())
    await state.set_state(OrderForm.glass_color)

@dp.message(OrderForm.glass_pattern)
async def process_glass_pattern_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=glass_pattern_kb())

# ─── FSM: GLASS COLOR (5) ───
@dp.message(OrderForm.glass_color, F.text.in_(GLASS_COLORS))
async def process_glass_color(message: types.Message, state: FSMContext):
    await state.update_data(glass_color=message.text)
    await message.answer(
        '6/8: Taxminiy o\'lchamlarni yozing (masalan: 80x200):',
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(OrderForm.dimensions)

@dp.message(OrderForm.glass_color)
async def process_glass_color_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=glass_color_kb())

# ─── FSM: DIMENSIONS (6) ───
@dp.message(OrderForm.dimensions, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_dimensions(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    existing = data.get('dimensions', '')
    if data.get('adding_more') and existing:
        text = existing + '\n' + text
    await state.update_data(dimensions=text, adding_more=False)
    await message.answer(
        '7/8: Buyurtma qiladigan mahsulotingizni soni?',
        reply_markup=quantity_choice_kb()
    )
    await state.set_state(OrderForm.quantity_choice)

@dp.message(OrderForm.dimensions)
async def process_dimensions_invalid(message: types.Message):
    await message.answer(        'Iltimos, o\'lchamlarni yozing (masalan: 80x200):')

# ─── FSM: QUANTITY CHOICE (7) ───
@dp.message(OrderForm.quantity_choice, F.text.in_(['Bitta', "Ko'p"]))
async def process_quantity_choice(message: types.Message, state: FSMContext):
    if message.text == 'Bitta':
        await state.update_data(quantity=1)
        await message.answer(
            '8/8 (oxirgi): Telefon raqamingizni yuboring yoki kontakt tugmasini bosing:',
            reply_markup=phone_kb()
        )
        await state.set_state(OrderForm.phone)
    else:
        await state.update_data(quantity=0)  # temporary, will be set after number input
        await message.answer(
            'Nechta dona buyurtma qilmoqchisiz? Raqamni kiriting:',
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(OrderForm.quantity_number)

@dp.message(OrderForm.quantity_choice)
async def process_quantity_choice_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=quantity_choice_kb())

# ─── FSM: QUANTITY NUMBER (7b) ───
@dp.message(OrderForm.quantity_number, lambda msg: msg.text and msg.text.strip().isdigit() and int(msg.text.strip()) > 0)
async def process_quantity_number(message: types.Message, state: FSMContext):
    qty = int(message.text.strip())
    await state.update_data(quantity=qty)
    await message.answer(
        'Yana o\'lcham qo\'shasizmi? (masalan: boshqa o\'lchamdagi oyna)',
        reply_markup=yes_no_kb()
    )
    await state.set_state(OrderForm.add_more)

@dp.message(OrderForm.quantity_number)
async def process_quantity_number_invalid(message: types.Message):
    await message.answer('Iltimos, faqat musbat son kiriting (masalan: 5):')

# ─── FSM: ADD MORE (7c) ───
@dp.message(OrderForm.add_more, F.text.in_(['Ha', "Yo'q"]))
async def process_add_more(message: types.Message, state: FSMContext):
    if message.text == 'Ha':
        await state.update_data(adding_more=True)
        await message.answer(
            'Qo\'shimcha o\'lchamni yozing:',
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(OrderForm.dimensions)
    else:
        await message.answer(
            '8/8 (oxirgi): Telefon raqamingizni yuboring yoki kontakt tugmasini bosing:',
            reply_markup=phone_kb()
        )
        await state.set_state(OrderForm.phone)

@dp.message(OrderForm.add_more)
async def process_add_more_invalid(message: types.Message):
    await message.answer('Iltimos, quyidagi tugmalardan birini tanlang:', reply_markup=yes_no_kb())

# ─── FSM: PHONE (8) ───
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
        glass_type=data.get('glass_type', 'Noma\'lum'),
        profile_color=data.get('profile_color', 'Noma\'lum'),
        dimensions=data.get('dimensions', 'Noma\'lum'),
        phone=data.get('phone', 'Noma\'lum'),
        glass_pattern=data.get('glass_pattern', 'Noma\'lum'),
        glass_color=data.get('glass_color', 'Noma\'lum'),
        quantity=data.get('quantity', 1)
    )
    dims = data['dimensions'].replace('\n', '\n     ')
    text = (
        '✅ Buyurtmangiz qabul qilindi!\n\n'
        f'📦 Material: {data["material"]}\n'
        f'🎨 Profil rangi: {data["profile_color"]}\n'
        f'🪟 Oyna qavati: {data["glass_type"]}\n'
        f'✨ Oyna naqshi: {data["glass_pattern"]}\n'
        f'🎯 Oyna rangi: {data["glass_color"]}\n'
        f'📐 O\'lchamlar: {dims}\n'
        f'🔢 Soni: {data["quantity"]} dona\n'
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
        'material_delivered': '🚚 Material olib kelinmoqda',
        'in_progress': '🔧 Ishlab chiqarish jarayonida',
        'ready': '✨ Oyna qismi tayyorlanmoqda',
        'delivered': '📦 To\'liq tayyor',
    }
    dims = order["dimensions"].replace('\n', '\n     ') if order["dimensions"] else '—'
    text = (
        f'🔍 Buyurtma ID: {order["order_id"]}\n\n'
        f'📦 Material: {order["material_type"]}\n'
        f'🎨 Profil rangi: {order["profile_color"]}\n'
        f'🪟 Oyna qavati: {order["glass_type"]}\n'
        f'✨ Oyna naqshi: {order["glass_pattern"] or "—"}\n'
        f'🎯 Oyna rangi: {order["glass_color"] or "—"}\n'
        f'📐 O\'lchamlar: {dims}\n'
        f'🔢 Soni: {order["quantity"] or 1} dona\n'
        f'📞 Telefon: {order["phone"]}\n'
        f'📊 Holati: {status_map.get(order["status"], order["status"])}\n'
        f'📅 Yaratilgan: {order["created_at"]}'
    )
    await message.answer(text)
    await state.clear()

# ─── BACKGROUND: NOTIFY ORDERS ───
async def notify_checker():
    while True:
        try:
            # 1) Material delivered notification (first confirmation)
            confirmed = get_unnotified_confirmations()
            for order in confirmed:
                dims = order["dimensions"].replace('\n', '\n     ') if order["dimensions"] else '—'
                text = (
                    f'🎉 Xushxabar!\n\n'
                    f'Sizning buyurtmangiz tasdiqlandi.\n'
                    f'🆔 ID raqamingiz: <b>{order["order_id"]}</b>\n\n'
                    f'📦 Material: {order["material_type"]}\n'
                    f'🎨 Profil rangi: {order["profile_color"]}\n'
                    f'🪟 Oyna qavati: {order["glass_type"]}\n'
                    f'✨ Oyna naqshi: {order["glass_pattern"] or "—"}\n'
                    f'🎯 Oyna rangi: {order["glass_color"] or "—"}\n'
                    f'📐 O\'lchamlar: {dims}\n'
                    f'🔢 Soni: {order["quantity"] or 1} dona\n'
                    f'📊 Holat: 🚚 Material olib kelinmoqda\n\n'
                    f'Buyurtmangiz holatini bot orqali kuzatib borishingiz mumkin: '
                    f'🔍 Buyurtmani tekshirish'
                )
                try:
                    await bot.send_message(order['telegram_id'], text, parse_mode='HTML')
                    mark_notified(order['order_id'])
                    logger.info(f'Confirmed notification sent to user {order["telegram_id"]} for order {order["order_id"]}')
                except Exception as e:
                    logger.error(f'Failed to notify user {order["telegram_id"]}: {e}')

            # 2) Delivered notification (final "tayyor" message)
            deliveries = get_unnotified_deliveries()
            for order in deliveries:
                text = (
                    f'🎉 Xushxabar! TriPro ustaxonasidan buyurtmangiz tayyor!\n\n'
                    f'Hurmatli mijoz, sizning ID: <b>{order["order_id"]}</b> raqamli buyurtmangiz '
                    f'barcha sifat nazoratlaridan muvaffaqiyatli o\'tdi va to\'liq tayyor bo\'ldi! 🛠✨\n\n'
                    f'🚚 Yetkazib berish va o\'rnatish:\n'
                    f'Bizning ustalarimiz siz yuborgan geolokatsiya bo\'yicha mahsulotlarni '
                    f'yuklab, yo\'lga chiqishga hozirlanmoqda.\n\n'
                    f'📞 Ustamiz yo\'lga chiqishdan oldin siz bilan aloqaga chiqadi. '
                    f'Iltimos, telefoningizni ochiq holda saqlang.\n\n'
                    f'TriPro-ni tanlaganingiz uchun rahmat! '
                    f'Uyingizga shinamlik va go\'zallik tilaymiz! 👍'
                )
                try:
                    await bot.send_message(order['telegram_id'], text, parse_mode='HTML')
                    mark_delivery_notified(order['order_id'])
                    logger.info(f'Delivery notification sent to user {order["telegram_id"]} for order {order["order_id"]}')
                except Exception as e:
                    logger.error(f'Failed to deliver-notify user {order["telegram_id"]}: {e}')
        except Exception as e:
            logger.error(f'Notify checker error: {e}')
        await asyncio.sleep(10)

# ─── MAIN FOR EXPORT ───
async def bot_main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(notify_checker())
    logger.info('Bot started polling...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    init_db()
    asyncio.run(bot_main())
