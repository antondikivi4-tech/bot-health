import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота и ID администратора
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set.")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID is not set.")

# Состояния анкеты
CHOOSING_GOAL, CHOOSING_FORMAT, ENTERING_CONTACT, CHOOSING_PAYMENT = range(4)

# Цены для разных вариантов
PRICES = {
    "nutrition": {"title": "Только питание", "price": "45 руб."},
    "training": {"title": "Тренировки", "price": "45 руб."},
    "full": {"title": "Полное сопровождение", "price": "75 руб."}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запуск анкетирования и выбор цели."""
    user = update.effective_user
    context.user_data.clear() # Очищаем данные при новом старте
    
    keyboard = [
        [InlineKeyboardButton("💪 Набор мышечной массы", callback_data="goal_mass")],
        [InlineKeyboardButton("🌟 Похудение", callback_data="goal_lose")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Выберите вашу цель:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_GOAL

async def goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора цели и переход к выбору формата."""
    query = update.callback_query
    await query.answer()
    
    goal = "Набор мышечной массы" if query.data == "goal_mass" else "Похудение"
    context.user_data['goal'] = goal
    
    keyboard = [
        [InlineKeyboardButton("🥗 Планирование питания", callback_data="format_nutrition")],
        [InlineKeyboardButton("🏋️‍♂️ Тренировки", callback_data="format_training")],
        [InlineKeyboardButton("🔥 Полное сопровождение", callback_data="format_full")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Цель: *{goal}*.\nТеперь выберите формат работы:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_FORMAT

async def format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора формата и запрос контактов."""
    query = update.callback_query
    await query.answer()
    
    format_key = query.data.replace("format_", "")
    context.user_data['format'] = format_key
    context.user_data['price_info'] = PRICES.get(format_key, {"title": "Не указано", "price": "0 руб."})
    
    await query.edit_message_text(
        text=f"Вы выбрали: *{context.user_data['price_info']['title']}* ({context.user_data['price_info']['price']}).\n\n"
             "Пожалуйста, отправьте вашим следующим сообщением ваш номер телефона или ник в Telegram (например, `@username`), чтобы мы могли с вами связаться.",
        parse_mode="Markdown"
    )
    return ENTERING_CONTACT

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение контактов и переход к выбору способа оплаты."""
    contact_text = update.message.text
    context.user_data['contact'] = contact_text
    
    keyboard = [
        [InlineKeyboardButton("💳 Картой онлайн", callback_data="pay_card")],
        [InlineKeyboardButton("🔄 ЕРИП / Перевод", callback_data="pay_erip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text="Отлично! Выберите удобный способ оплаты:",
        reply_markup=reply_markup
    )
    return CHOOSING_PAYMENT

async def payment_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Фиксация оплаты, сохранение анкеты и отправка отчета администратору."""
    query = update.callback_query
    await query.answer()
    
    pay_method = "Картой онлайн" if query.data == "pay_card" else "ЕРИП / Перевод"
    context.user_data['payment'] = pay_method
    
    # Сборка данных о пользователе
    user = update.effective_user
    goal = context.user_data.get('goal', '-')
    fmt = context.user_data.get('price_info', {}).get('title', '-')
    price = context.user_data.get('price_info', {}).get('price', '-')
    contact = context.user_data.get('contact', '-')
    
    # Сообщение клиенту
    await query.edit_message_text(
        text=f"Спасибо за заявку! 🎉\n\n"
             f"📋 *Ваша анкета:*\n"
             f"• Цель: {goal}\n"
             f"• Формат: {fmt} ({price})\n"
             f"• Контакт: {contact}\n"
             f"• Оплата: {pay_method}\n\n"
             f"В ближайшее время мы свяжемся с вами!",
        parse_mode="Markdown"
    )
    
    # Отправка уведомления администратору
    admin_message = (
         f"🔔 *Новая заявка от клиента!*\n\n"
         f"👤 Пользователь: @{user.username or 'нет юзернейма'} (ID: `{user.id}`)\n"
         f"🎯 Цель: {goal}\n"
         f"📦 Формат: {fmt} — *{price}*\n"
         f"📞 Связь: {contact}\n"
         f"💳 Способ оплаты: {pay_method}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена заполнения анкеты."""
    await update.message.reply_text("Анкета отменена. Чтобы начать заново, отправьте /start")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()

    # Настройка ConversationHandler для пошагового опросника
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_GOAL: [CallbackQueryHandler(goal_chosen, pattern="^goal_")],
            CHOOSING_FORMAT: [CallbackQueryHandler(format_chosen, pattern="^format_")],
            ENTERING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_received)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(payment_chosen, pattern="^pay_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    logger.info("Бот запущен и готов к работе...")
    application.run_polling()

if __name__ == "__main__":
    main()
