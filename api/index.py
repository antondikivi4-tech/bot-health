import os
import json
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = "ВАШ_АДМИН_CHAT_ID"  # Замените на ваш реальный Chat ID

# Временное хранилище анкет в памяти
user_data_storage = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_invoice(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": "Индивидуальный план (Питание + Тренировки)",
        "description": "Разработка персональной программы тренировок и плана питания под ваши цели.",
        "payload": "fitness_plan_order",
        "provider_token": "",  # Пустая строка обязательна для Telegram Stars (XTR)
        "currency": "XTR",     # Валюта Telegram Stars
        "prices": [{"label": "План Питания и Тренировок", "amount": 500}]  # 500 Звезд (можно изменить сумму)
    }
    requests.post(url, json=payload)

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🔥 Заполнить полную анкету и заказать", "callback_data": "start_survey"}]
        ]
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data.decode('utf-8'))
        except Exception:
            self.send_response(200)
            self.end_headers()
            return

        # Обработка предварительного запроса чека (нужно для Stars)
        if "pre_checkout_query" in update:
            query = update["pre_checkout_query"]
            query_id = query["id"]
            url = f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery"
            requests.post(url, json={"pre_checkout_query_id": query_id, "ok": True})
            self.send_response(200)
            self.end_headers()
            return

        # Нажатие на инлайн-кнопки
        if "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            data = query["data"]
            
            if data == "start_survey":
                user_data_storage[chat_id] = {"step": 1, "answers": {}}
                send_message(
                    chat_id,
                    "📋 *Шаг 1 из 3: База и Антропометрия*\n\n"
                    "Пожалуйста, напишите одним сообщением:\n"
                    "• Пол и возраст\n"
                    "• Рост и актуальный вес\n"
                    "• Тип телосложения и проблемные зоны\n"
                    "• Главная задача (похудение, набор массы, рекомпозиция)"
                )

        # Текстовые сообщения от пользователя
        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user = message.get("from", {})
            username = user.get("username", "нет юзернейма")
            first_name = user.get("first_name", "Клиент")

            # Обработка успешной оплаты Telegram Stars
            if "successful_payment" in message:
                payment = message["successful_payment"]
                total_amount = payment["total_amount"]
                
                ans = user_data_storage.get(chat_id, {}).get("answers", {})
                full_report = (
                    "💰 *ОПЛАЧЕНО ЧЕРЕЗ TELEGRAM STARS!* 🎉\n\n"
                    f"👤 Имя: {first_name} (@{username})\n"
                    f"🆔 Chat ID: `{chat_id}`\n"
                    f"💵 Сумма: {total_amount} ⭐\n\n"
                    f"📌 *1. База и цели:*\n{ans.get('step_1', 'Нет данных')}\n\n"
                    f"📌 *2. Активность и здоровье:*\n{ans.get('step_2', 'Нет данных')}\n\n"
                    f"📌 *3. Питание и тренировки:*\n{ans.get('step_3', 'Нет данных')}"
                )

                if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "ВАШ_АДМИН_CHAT_ID":
                    send_message(ADMIN_CHAT_ID, full_report)

                send_message(
                    chat_id,
                    "✅ *Оплата прошла успешно! Спасибо!*\n\n"
                    "Ваша анкета и средства получены. Тренер уже приступил к индивидуальной разработке вашей программы."
                )
                
                if chat_id in user_data_storage:
                    del user_data_storage[chat_id]
                
                self.send_response(200)
                self.end_headers()
                return

            if text == "/start":
                welcome_text = (
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок "
                    "для занятий в любом удобном месте.\n\n"
                    "Нажми кнопку ниже, чтобы заполнить анкету и оформить заказ:"
                )
                send_message(chat_id, welcome_text, reply_markup=main_menu())
            
            elif chat_id in user_data_storage:
                step = user_data_storage[chat_id]["step"]

                if step == 1:
                    user_data_storage[chat_id]["answers"]["step_1"] = text
                    user_data_storage[chat_id]["step"] = 2
                    send_message(
                        chat_id,
                        "🏃‍♂️ *Шаг 2 из 3: Образ жизни, Активность и Здоровье*\n\n"
                        "Напишите:\n"
                        "• Тип работы и режим сна\n"
                        "• Текущие тренировки и шаги в день\n"
                        "• Уровень подготовки\n"
                        "• Травмы, боли и хронические заболевания"
                    )
                elif step == 2:
                    user_data_storage[chat_id]["answers"]["step_2"] = text
                    user_data_storage[chat_id]["step"] = 3
                    send_message(
                        chat_id,
                        "🥗 *Шаг 3 из 3: Питание, Условия и Быт*\n\n"
                        "Последний блок вопросов:\n"
                        "• Где будут тренировки и доступный инвентарь\n"
                        "• Желаемый график тренировок\n"
                        "• Приемы пищи, предпочтения и аллергии\n"
                        "• Бюджет и отношения с едой"
                    )
                elif step == 3:
                    user_data_storage[chat_id]["answers"]["step_3"] = text
                    
                    # Анкета завершена — отправляем счет на оплату в Звездах (XTR)
                    send_message(
                        chat_id,
                        "✅ *Анкета полностью заполнена!*\n\n"
                        "Для старта работы над вашей программой осталось произвести оплату. Нажмите кнопку ниже:"
                    )
                    send_invoice(chat_id)

            else:
                send_message(chat_id, "Чтобы начать, отправьте команду /start")

        self.send_response(200)
        self.end_headers()
        return
