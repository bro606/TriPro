import asyncio
import os
import sys
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, save_akfa_order, get_order, get_unnotified_confirmations, mark_notified, get_unnotified_deliveries, mark_delivery_notified

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
if BOT_TOKEN:
    BOT_TOKEN = BOT_TOKEN.strip()
else:
    BOT_TOKEN = '8745687733:AAFmfV5n6f0Z0RxJ70aXVf82zNa0LI3KUs4'

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'SizningUsername')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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

BACK_BTN = '🔙 Bosh sahifaga'

def back_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BACK_BTN, callback_data='back_to_menu')],
    ])

def workshops_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🪟 AKFA rom va eshiklar', callback_data='ws_akfa')],
        [InlineKeyboardButton(text='🪵 Yog\'och mahsulotlari', callback_data='ws_yogoch')],
        [InlineKeyboardButton(text='💎 Shisha xizmatlari', callback_data='ws_shisha')],
    ])

def phone_choice_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Kontaktni ulash', request_contact=True)],
            [KeyboardButton(text='⌨️ Raqamni yozish')],
            [KeyboardButton(text=BACK_BTN)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
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

def admin_contact_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👨‍💻 Admin bilan bog\'lanish', url=f'https://t.me/{ADMIN_USERNAME}')],
    ])

def back_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔍 Buyurtmani tekshirish', callback_data='check_order')],
        [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='back_to_menu')],
    ])

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        f'Assalomu alaykum, {message.from_user.first_name}! 👋\n\n'
        f'TriPro — AKFA romlar, yog\'och va shisha mahsulotlari ishlab chiqaruvchi '
        f'professional ustaxona.\n\n'
        f'Quyidagi yo\'nalishlardan birini tanlang:',
        reply_markup=workshops_kb()
    )

@dp.message(Command('cancel'))
@dp.message(Command('bosh_menu'))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Bosh menyu:', reply_markup=workshops_kb())

@dp.callback_query(lambda c: c.data == 'back_to_menu')
async def cb_back_to_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text(
        'Quyidagi yo\'nalishlardan birini tanlang:',
        reply_markup=workshops_kb()
    )

@dp.callback_query(lambda c: c.data == 'ws_akfa')
async def cb_ws_akfa(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(AkfaForm.name)
    await call.message.edit_text(
        '🪟 AKFA rom va eshiklar bo\'limi\n\n1/9: Ismingizni kiriting:',
        reply_markup=back_inline_kb()
    )

@dp.callback_query(lambda c: c.data == 'ws_yogoch')
async def cb_ws_yogoch(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(
        '🪵 Yog\'och mahsulotlari\n\n'
        'Siz tanlagan yo\'nalish bo\'yicha buyurtmalar individual tartibda qabul qilinadi. '
        'Aniq narxlar va dizayn masalalari bo\'yicha bizning bosh mutaxassisimiz bilan '
        'bevosita bog\'laning.',
        reply_markup=admin_contact_kb()
    )

@dp.callback_query(lambda c: c.data == 'ws_shisha')
async def cb_ws_shisha(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(
        '💎 Shisha xizmatlari\n\n'
        'Siz tanlagan yo\'nalish bo\'yicha buyurtmalar individual tartibda qabul qilinadi. '
        'Aniq narxlar va dizayn masalalari bo\'yicha bizning bosh mutaxassisimiz bilan '
        'bevosita bog\'laning.',
        reply_markup=admin_contact_kb()
    )

@dp.message(AkfaForm.name, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AkfaForm.surname)
    await message.answer('2/9: Familiyangizni kiriting:', reply_markup=back_inline_kb())

@dp.message(AkfaForm.name)
async def process_name_invalid(message: types.Message):
    await message.answer('Iltimos, ismingizni yozing:', reply_markup=back_inline_kb())

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

@dp.message(AkfaForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(AkfaForm.material)
    await message.answer('4/9: Material turini tanlang:', reply_markup=material_ikb())

@dp.message(AkfaForm.phone, F.text == '⌨️ Raqamni yozish')
async def process_phone_manual_choice(message: types.Message, state: FSMContext):
    await message.answer(
        'Iltimos, telefon raqamingizni kiriting (masalan: +998901234567):',
        reply_markup=back_inline_kb()
    )

@dp.message(AkfaForm.phone, lambda msg: msg.text and len(msg.text.strip()) > 5 and msg.text.strip() != BACK_BTN)
async def process_phone_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(AkfaForm.material)
    await message.answer('4/9: Material turini tanlang:', reply_markup=material_ikb())

@dp.message(AkfaForm.phone, F.text == BACK_BTN)
async def process_phone_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer('Bosh menyu:', reply_markup=workshops_kb())

@dp.message(AkfaForm.phone)
async def process_phone_invalid(message: types.Message):
    await message.answer(
        'Iltimos, kontakt tugmasini bosing yoki raqamingizni yozing:',
        reply_markup=phone_choice_kb()
    )

@dp.callback_query(AkfaForm.material, lambda c: c.data.startswith('mat_'))
async def cb_material(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    vals = {'mat_plastik': 'Plastik', 'mat_alyumin': 'Alyumin'}
    await state.update_data(material=vals[call.data])
    await state.set_state(AkfaForm.glass_layer)
    await call.message.edit_text('5/9: Oyna qavatini tanlang:', reply_markup=glass_layer_ikb())

@dp.callback_query(AkfaForm.glass_layer, lambda c: c.data.startswith('glass_'))
async def cb_glass_layer(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    vals = {'glass_1': '1 qavatli', 'glass_2': '2 qavatli'}
    await state.update_data(glass_layer=vals[call.data])
    await state.set_state(AkfaForm.profile_color)
    await call.message.edit_text('6/9: Profil rangini tanlang:', reply_markup=profile_color_ikb())

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

@dp.message(AkfaForm.dimensions, lambda msg: msg.text and len(msg.text.strip()) > 0)
async def process_dimensions(message: types.Message, state: FSMContext):
    await state.update_data(dimensions=message.text.strip())
    await state.set_state(AkfaForm.quantity)
    await message.answer('8/9: Mahsulot sonini yozing (masalan: 2):', reply_markup=back_inline_kb())

@dp.message(AkfaForm.dimensions)
async def process_dimensions_invalid(message: types.Message):
    await message.answer('Iltimos, o\'lchamlarni yozing (masalan: 80x90):', reply_markup=back_inline_kb())

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

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'confirm_yes')
async def cb_confirm_yes(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    save_akfa_order(
        telegram_id=call.from_user.id,
        name=data.get('name', ''),
        surname=data.get('surname', ''),
        phone=data.get('phone', ''),
        material=data.get('material', 'Noma\'lum'),
        glass_layer=data.get('glass_layer', 'Noma\'lum'),
        profile_color=data.get('profile_color', 'Noma\'lum'),
        dimensions=data.get('dimensions', 'Noma\'lum'),
        quantity=data.get('quantity', 1),
    )
    await state.clear()
    await call.message.edit_text(
        '✅ Arizangiz qabul qilindi, mutaxassisimiz tez orada siz bilan bog\'lanadi.\n\n'
        f'👤 Ism: {data["name"]} {data["surname"]}\n'
        f'📞 Telefon: {data["phone"]}\n'
        f'🛠 Material: {data["material"]}\n'
        f'🪟 Oyna qavati: {data["glass_layer"]}\n'
        f'🎨 Rang: {data["profile_color"]}\n'
        f'📐 O\'lcham: {data["dimensions"]}\n'
        f'📦 Soni: {data["quantity"]} ta',
        reply_markup=back_menu_kb()
    )

@dp.callback_query(AkfaForm.confirm, lambda c: c.data == 'confirm_retry')
async def cb_confirm_retry(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(AkfaForm.name)
    await call.message.edit_text(
        '🪟 AKFA rom va eshiklar bo\'limi\n\n1/9: Ismingizni kiriting:',
        reply_markup=back_inline_kb()
    )

@dp.callback_query(lambda c: c.data == 'check_order')
async def cb_check_order(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer('Iltimos, 4 xonali buyurtma ID raqamingizni kiriting:')
    await state.set_state('check_order_input')

@dp.message(StateFilter('check_order_input'))
async def process_check_order(message: types.Message, state: FSMContext):
    oid = message.text.strip()
    if not oid.isdigit() or len(oid) != 4:
        await message.answer('Iltimos, to\'g\'ri 4 xonali ID raqamini kiriting (masalan: 3487):')
        return
    order = get_order(oid)
    if not order:
        await message.answer('❌ Bunday ID raqamli buyurtma topilmadi.', reply_markup=back_menu_kb())
        await state.clear()
        return
    status_map = {
        'pending': '⏳ Kutilmoqda',
        'confirmed': '✅ Tasdiqlangan',
        'material_delivered': '🚚 Material olib kelinmoqda',
        'in_progress': '🔧 Ishlab chiqarish jarayonida',
        'ready': '✨ Tayyorlanmoqda',
        'delivered': '📦 To\'liq tayyor',
    }
    dims = order["dimensions"].replace('\n', '\n     ') if order["dimensions"] else '—'
    text = (
        f'🔍 Buyurtma ID: {order["order_id"]}\n\n'
        f'📦 Material: {order["material_type"]}\n'
        f'🎨 Profil rangi: {order["profile_color"]}\n'
        f'🪟 Oyna qavati: {order["glass_type"]}\n'
        f'📐 O\'lchamlar: {dims}\n'
        f'📞 Telefon: {order["phone"]}\n'
        f'📊 Holati: {status_map.get(order["status"], order["status"])}\n'
        f'📅 Yaratilgan: {order["created_at"]}'
    )
    await message.answer(text, reply_markup=back_menu_kb())
    await state.clear()

async def notify_checker():
    while True:
        try:
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
                    f'📐 O\'lchamlar: {dims}\n'
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

async def run_web_server():
    app = web.Application()
    app.router.add_get('/health', lambda r: web.json_response({'status': 'ok'}))
    runner = web.AppRunner(app)
    await runner.setup()
    PORT = int(os.environ.get('PORT', 8000))
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f'Web server running on 0.0.0.0:{PORT}')

async def bot_main(start_web_server=True):
    if start_web_server:
        await run_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(notify_checker())
    logger.info('Bot started polling...')
    await dp.start_polling(bot)

if __name__ == '__main__':
    init_db()
    asyncio.run(bot_main())
