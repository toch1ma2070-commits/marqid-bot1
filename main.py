import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Ваши данные
TOKEN = "9091951549:AAGgAjwypi8XrNnMYqoFRXdExQC9MFo79pY"
ADMIN_ID = 8265261922     

# Реквизиты для оплаты
BANK_NAME = "ЮMoney"
PHONE_NUMBER = "+79801842066"
RECEIVER_NAME = "Диана Н."

# Товары, цены и файлы
PRICES = {
    "legit": {
        "name": "Legit конфиг", 
        "price": 60, 
        "file": "legit.cfg"
    },
    "rage": {
        "name": "Rage конфиг", 
        "price": 75, 
        "file": "rage.cfg"
    },
    "hvh": {
        "name": "HVH конфиг", 
        "price": 100, 
        "file": "hvh.cfg"
    }
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для FSM (поддержка и ответы админа)
class SupportState(StatesGroup):
    waiting_for_question = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply_text = State()

# Главное меню
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Legit — 60 руб.", callback_data="buy_legit")],
        [InlineKeyboardButton(text="🔥 Rage — 75 руб.", callback_data="buy_rage")],
        [InlineKeyboardButton(text="⚡ HVH — 100 руб.", callback_data="buy_hvh")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support_start")]
    ])

# 1. Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Выберите товар для покупки или напишите в поддержку:",
        reply_markup=get_main_keyboard()
    )

# --- БЛОК ПОДДЕРЖКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---

@dp.callback_query(F.data == "support_start")
async def support_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportState.waiting_for_question)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="support_cancel")]
    ])
    await callback.message.edit_text(
        "💬 **Служба поддержки**\n\n"
        "Напишите ваш вопрос или опишите проблему одним сообщением, и администратор ответит вам в ближайшее время.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "support_cancel")
async def support_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Привет! Выберите товар для покупки или напишите в поддержку:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer("Отменено")

@dp.message(SupportState.waiting_for_question)
async def support_receive_message(message: Message, state: FSMContext):
    user = message.from_user
    text = message.text
    await state.clear()
    
    # Отправляем подтверждение пользователю
    await message.answer("✅ Ваше сообщение отправлено в поддержку! Ожидайте ответ.", reply_markup=get_main_keyboard())
    
    # Кнопка для ответа администратора
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"ans_{user.id}")]
    ])
    
    # Пересылаем сообщение вам в ЛС
    username_str = f"@{user.username}" if user.username else "скрыт"
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💬 **Новое сообщение в поддержку!**\n\n"
             f"От: {username_str} (ID: `{user.id}`)\n"
             f"Имя: {user.first_name}\n\n"
             f"Текст:\n{text}",
        reply_markup=admin_keyboard,
        parse_mode="Markdown"
    )

# --- БЛОК ОТВЕТА АДМИНА ---

@dp.callback_query(F.data.startswith("ans_"))
async def admin_start_reply(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав!", show_alert=True)
        return
        
    user_id = int(callback.data.split("_")[1])
    await state.set_state(AdminReplyState.waiting_for_reply_text)
    await state.update_data(reply_to_user=user_id)
    
    await callback.message.answer(f"✍️ Введите текст ответа для пользователя (ID: `{user_id}`):", parse_mode="Markdown")
    await callback.answer()

@dp.message(AdminReplyState.waiting_for_reply_text)
async def admin_send_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    data = await state.get_data()
    user_id = data.get("reply_to_user")
    reply_text = message.text
    
    await state.clear()
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"👨‍💻 **Ответ от поддержки:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ответ успешно отправлен пользователю!")
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить сообщение пользователю (возможно, он заблокировал бота): {e}")

# --- МАГАЗИН И ПОКУПКИ ---

# 2. Выбор товара и показ реквизитов
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    item = PRICES.get(category)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Я оплатил(а), отправить чек", callback_data=f"paid_{category}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])

    await callback.message.edit_text(
        f"📦 Вы выбрали: <b>{item['name']}</b>\n"
        f"💰 К оплате: <b>{item['price']} руб.</b>\n\n"
        f"💳 <b>Реквизиты для перевода (СБП):</b>\n"
        f"Банк: <code>{BANK_NAME}</code>\n"
        f"Номер: <code>{PHONE_NUMBER}</code>\n"
        f"Получатель: <code>{RECEIVER_NAME}</code>\n\n"
        f"⚠️ <i>Обязательно переведите точную сумму ({item['price']} руб.). После оплаты нажмите кнопку ниже.</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Привет! Выберите товар для покупки или напишите в поддержку:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# 3. Пользователь нажимает «Я оплатил»
@dp.callback_query(F.data.startswith("paid_"))
async def process_paid(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    item = PRICES.get(category)
    user = callback.from_user
    
    await callback.message.edit_text(
        "⏳ **Заявка принята!**\n\n"
        "Администратор проверяет поступление средств. Как только деньги придут, бот пришлет вам файл.",
        parse_mode="Markdown"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить и выдать файл", callback_data=f"give_{user.id}_{category}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"cancel_{user.id}")]
    ])
    
    username_str = f"@{user.username}" if user.username else "скрыт"
    # Уведомление приходит вам в ЛС
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **Новый заказ!**\n\n"
             f"Пользователь: {username_str} (ID: `{user.id}`)\n"
             f"Товар: <b>{item['name']}</b> ({item['price']} руб.)\n\n"
             f"Проверьте ЮMoney, поступил ли перевод.",
        reply_markup=admin_keyboard,
        parse_mode="Markdown"
    )
    await callback.answer("Уведомление отправлено администратору!")

# 4. Вы подтверждаете оплату — бот отправляет файл покупателю
@dp.callback_query(F.data.startswith("give_"))
async def admin_give_product(callback: CallbackQuery):
    _, user_id_str, category = callback.data.split("_")
    user_id = int(user_id_str)
    item = PRICES.get(category)
    
    file_to_send = item["file"]

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 **Оплата подтверждена!** Вот ваш файл для *{item['name']}*:",
            parse_mode="Markdown"
        )
        await bot.send_document(
            chat_id=user_id,
            document=FSInputFile(file_to_send)
        )
        await callback.message.edit_text(f"✅ Файл успешно отправлен пользователю (ID: {user_id})!")
    except Exception as e:
        await callback.message.edit_text(f"⚠️ Ошибка при отправке файла: {e}")
        
    await callback.answer()

# Кнопка отмены заказа для админа
@dp.callback_query(F.data.startswith("cancel_"))
async def admin_cancel(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(chat_id=user_id, text="❌ Ваша оплата была отклонена администратором. Если это ошибка, напишите в поддержку.")
    except:
        pass
    await callback.message.edit_text("❌ Заказ отклонен.")
    await callback.answer()

# Запуск
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
