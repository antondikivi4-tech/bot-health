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

# Токен бота и ID администратора (для уведомлений об оплате)
TOKEN = os.getenv("TELEGRAM_TOKEN", "ВАШ_ТОКЕН_БОТА")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "ВАШ_ADMIN_ID")

# Состояния анкеты
CHOOSING_GOAL, CHOOSING_FORMAT, ENTERING_CONTACT, CHOOSING_PAYMENT = range(4)

# Цены
PRICES = {
    "by_rub": {"currency": "BYN", "nutrition": "45 руб.", "training": "45 руб.", "full": "75 руб."},
    "ru_rub": {"currency": "RUB", "nutrition": "1300 руб.", "training": "1300 руб.", "full": "2200 руб."}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("🔥 Получить план питания и тренировок", callback_data="start_quest")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот проекта **Культура тела**. Помогу вам достичь вашей физической формы в любом удобном месте!\n"
        "Давайте подберем для вас персональную программу.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def start_quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💪 Набор мышечной массы", callback_data="goal_mass")],
        [InlineKeyboardButton("🔥 Жиросжигание / Похудение", callback_data="goal_fat")],
        [InlineKeyboardButton("⚖️ Рекомпозиция (масса + жиросжигание)", callback_data="goal_recomp")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "**Шаг 1 из 3:** Какая ваша главная цель?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_GOAL

async def goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    goals = {
        "goal_mass": "Набор мышечной массы",
        "goal_fat": "Жиросжигание / Похудение",
        "goal_recomp": "Рекомпозиция"
    }
    context.user_data["goal"] = goals.get(query.data, "Не указано")
    
    keyboard = [
        [InlineKeyboardButton("🍏 Только Питание", callback_data="format_nut")],
        [InlineKeyboardButton("🏋️‍♂️ Только Тренировки", callback_data="format_train")],
        [InlineKeyboardButton("⭐ Питание + Тренировки (Всё включено)", callback_data="format_full")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "**Шаг 2 из 3:** Выберите формат программы:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_FORMAT

async def format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    formats = {
        "format_nut": "Питание",
        "format_train": "Тренировки",
        "format_full": "Питание + Тренировки"
    }
    context.user_data["format_key"] = query.data
    context.user_data["format_name"] = formats.get(query.data, "Не указано")
    
    await query.edit_message_text(
        "**Шаг 3 из 3:** Напишите ваш **Telegram для связи** (например, @username) или номер телефона, чтобы мы могли отправить вам готовый план после оплаты:",
        parse_mode="Markdown"
    )
    return ENTERING_CONTACT

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.text
    context.user_data["contact"] = contact
    
    keyboard = [
        [InlineKeyboardButton("🇧🇾 Беларусь (Бел. руб / Альфа-Банк)", callback_data="pay_by")],
        [InlineKeyboardButton("🇷🇺 Россия (Рос. руб / Сбер Банк)", callback_data="pay_ru")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "✅ Анкета заполнена!\n\n"
        f"🎯 **Цель:** {context.user_data['goal']}\n"
        f"📋 **Формат:** {context.user_data['format_name']}\n"
        f"👤 **Контакт:** {contact}\n\n"
        "💳 **Выберите удобный способ оплаты и валюту:**"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return CHOOSING_PAYMENT

async def payment_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pay_type = query.data
    format_key = context.user_data.get("format_key", "format_full")
    
    if pay_type == "pay_by":
        if format_key == "format_nut":
            price = PRICES["by_rub"]["nutrition"]
        elif format_key == "format_train":
            price = PRICES["by_rub"]["training"]
        else:
            price = PRICES["by_rub"]["full"]
            
        payment_instructions = (
            f"🛒 К оплате: **{price}**\n\n"
            "**Реквизиты Альфа-Банк (Беларусь):**\n"
            "• Счет получателя: `BY38ALFA3014317T0K0010270000`\n"
            "• Назначение платежа: Оплата информационных услуг\n\n"
            "⚠️ **Важно:** После совершения платежа отправьте чек (фото или скриншот) сюда в чат или напишите нашему менеджеру @AVDDESINGSTUDIO, и мы сразу начнем подготовку вашей программы!"
        )
    else:
        if format_key == "format_nut":
            price = PRICES["ru_rub"]["nutrition"]
        elif format_key == "format_train":
            price = PRICES["ru_rub"]["training"]
        else:
            price = PRICES["ru_rub"]["full"]
            
        payment_instructions = (
            f"🛒 К оплате: **{price}**\n\n"
            "**Оплата из России (Сбер Банк Беларусь):**\n"
            "Вы можете перевести средства по номеру счета:\n\n"
            "• Банк: Сбер Банк (Беларусь)\n"
            "• Счет получателя: `BY58BPSB3014R000000000275330`\n\n"
            "⚠️ **Важно:** После перевода обязательно отправьте скриншот чека сюда в чат или нашему менеджеру @AVDDESINGSTUDIO."
        )

    # Уведомление администратору
    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "ВАШ_ADMIN_ID":
        try:
            admin_msg = (
                f"🔔 **Новая заявка на оплату!**\n"
                f"• Цель: {context.user_data.get('goal')}\n"
                f"• Формат: {context.user_data.get('format_name')}\n"
                f"• Контакт: {context.user_data.get('contact')}\n"
                f"• Регион: {'Беларусь (Альфа)' if pay_type == 'pay_by' else 'Россия (Сбер)'}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")

    await query.edit_message_text(payment_instructions, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог сброшен. Чтобы начать заново, отправьте /start.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_GOAL: [CallbackQueryHandler(goal_chosen, pattern="^goal_")],
            CHOOSING_FORMAT: [CallbackQueryHandler(format_chosen, pattern="^format_")],
            ENTERING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contact_received)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(payment_selected, pattern="^pay_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(start_quest, pattern="^start_quest$"))

    application.run_polling()

if __name__ == "__main__":
    main()
