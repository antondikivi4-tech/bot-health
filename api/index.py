import os
import json
import logging
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

CHOOSING_GOAL, CHOOSING_FORMAT, ENTERING_CONTACT, CHOOSING_PAYMENT = range(4)

PRICES = {
    "nutrition": {"title": "Только питание", "price": "45 руб."},
    "training": {"title": "Тренировки", "price": "45 руб."},
    "full": {"title": "Полное сопровождение", "price": "75 руб."}
}

# Инициализация приложения python-telegram-bot
ptb_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("💪 Набор мышечной массы", callback_data="goal_mass")],
        [InlineKeyboardButton("🌟 Похудение", callback_data="goal_lose")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Привет, {user.first_name}! Выберите вашу цель:", reply_markup=reply_markup)
    return CHOOSING_GOAL

async def goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    await query.edit_message_text(text=f"Цель: *{goal}*.\nТеперь выберите формат работы:", reply_markup=reply_markup, parse_mode="Markdown")
    return CHOOSING_FORMAT

async def format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    format_key = query.data.replace("format_", "")
    context.user_data['format'] = format_key
    context.user_data['price_info'] = PRICES.get(format_key, {"title": "Не указано", "price": "0 руб."})
    await query.edit_message_text(
        text=f"Вы выбрали: *{context.user_data['price_info']['title']}* ({context.user_data['price_info']['price']}).\n\n"
             "Пожалуйста, отправьте вашим следующим сообщением ваш номер телефона или ник в Telegram.",
        parse_mode="Markdown"
    )
    return ENTERING_CONTACT

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact_text = update.message.text
    context.user_data['contact'] = contact_text
    keyboard = [
        [InlineKeyboardButton("💳 Картой онлайн", callback_data="pay_card")],
        [InlineKeyboardButton("🔄 ЕРИП / Перевод", callback_data="pay_erip")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text="Отлично! Выберите удобный способ оплаты:", reply_markup=reply_markup)
    return CHOOSING_PAYMENT

async def payment_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pay_method = "Картой онлайн" if query.data == "pay_card" else "ЕРИП / Перевод"
    user = update.effective_user
    goal = context.user_data.get('goal', '-')
    fmt = context.user_data.get('price_info', {}).get('title', '-')
    price = context.user_data.get('price_info', {}).get('price', '-')
    contact = context.user_data.get('contact', '-')
    
    await query.edit_message_text(
        text=f"Спасибо за заявку! 🎉\n\n• Цель: {goal}\n• Формат: {fmt} ({price})\n• Контакт: {contact}\n• Оплата: {pay_method}",
        parse_mode="Markdown"
    )
    
    admin_message = f"🔔 *Новая заявка!*\n👤 @{user.username or 'нет'} (ID: `{user.id}`)\n🎯 {goal}\n📦 {fmt} — *{price}*\n📞 {contact}\n💳 {pay_method}"
    try:
        await ptb_app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
    return ConversationHandler.END

# Регистрируем обработчики (ConversationHandler лучше заменить на простую логику состояний для вебхуков, но базово структура сохраняется)
# Для примера на Vercel часто делают упрощенный роутинг или используют готовые шаблоны без тяжелых конвееров.
