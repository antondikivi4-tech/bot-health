import os
import json
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = "673791974"

user_data_storage = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_invoice(chat_id, plan_type, amount):
    titles = {
        "base": "🥉 Базовый план", 
        "std": "🥈 Стандарт (Питание + Тренировки)", 
        "vip": "🥇 VIP (План + 2 недели ведения)",
        "month": "💎 Месячное ведение (Полный контроль)"
    }
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": titles[plan_type],
        "description": "Персональная программа трансформации тела под ваши цели.",
        "payload": f"order_{plan_type}",
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": "Стоимость", "amount": amount}]
    }
    requests.post(url, json=payload)

def payment_methods_menu():
    return {
        "inline_keyboard": [
            [{"text": "🥉 Выбрать Базовый (300 ⭐)", "callback_data": "base_plan"}],
            [{"text": "🥈 Выбрать Стандарт (500 ⭐)", "callback_data": "std_plan"}],
            [{"text": "🥇 Выбрать VIP (1000 ⭐)", "callback_data": "vip_plan"}],
            [{"text": "💎 Выбрать Месячное ведение (1500 ⭐)", "callback_data": "month_plan"}]
        ]
    }

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🔥 Заполнить анкету", "callback_data": "start_survey"}]
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

        if "pre_checkout_query" in update:
            query_id = update["pre_checkout_query"]["id"]
            requests.post(f"https://api.telegram.org/bot{TOKEN}/answerPreCheckoutQuery", 
                          json={"pre_checkout_query_id": query_id, "ok": True})
            self.send_response(200)
            self.end_headers()
            return

        if "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            data = query["data"]
            
            if data == "start_survey":
                user_data_storage[chat_id] = {"step": 1, "answers": {}}
                send_message(
                    chat_id,
                    "📋 *Шаг 1 из 3: База и Антропометрия*\n\n"
                    "Напишите одним сообщением:\n"
                    "• Пол, возраст, рост и актуальный вес\n"
                    "• Тип телосложения и главная задача (похудение/масса)"
                )
            elif data in ["base_plan", "std_plan", "vip_plan", "month_plan"]:
                amounts = {"base_plan": 300, "std_plan": 500, "vip_plan": 1000, "month_plan": 1500}
                plan_map = {"base_plan": "base", "std_plan": "std", "vip_plan": "vip", "month_plan": "month"}
                send_invoice(chat_id, plan_map[data], amounts[data])

        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user = message.get("from", {})
            username = user.get("username", "нет юзернейма")
            first_name = user.get("first_name", "Клиент")

            if "successful_payment" in message:
                payment = message["successful_payment"]
                total_amount = payment["total_amount"]
                
                ans = user_data_storage.get(chat_id, {}).get("answers", {})
                full_report = (
                    "💰 *НОВАЯ ОПЛАТА УСПЕШНО ПРОШЛА!* 🎉\n\n"
                    f"👤 Имя: {first_name} (@{username})\n"
                    f"🆔 Chat ID: `{chat_id}`\n"
                    f"💵 Сумма: {total_amount} ⭐\n\n"
                    f"📌 *1. База:*\n{ans.get('step_1', '-')}\n\n"
                    f"📌 *2. Активность и здоровье:*\n{ans.get('step_2', '-')}\n\n"
                    f"📌 *3. Питание и цели:*\n{ans.get('step_3', '-')}"
                )

                if ADMIN_CHAT_ID:
                    send_message(ADMIN_CHAT_ID, full_report)

                send_message(
                    chat_id,
                    "✅ *Оплата получена! Спасибо!*\n\n"
                    "Ваша анкета у тренера. Скоро начнется работа по вашему тарифу!"
                )
                if chat_id in user_data_storage:
                    del user_data_storage[chat_id]
                
                self.send_response(200)
                self.end_headers()
                return

            if text == "/start":
                welcome_text = (
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок "
                    "для занятий в любом удобном месте, а также взять тебя на полное ведение.\n\n"
                    "Нажми кнопку ниже:"
                )
                send_message(chat_id, welcome_text, reply_markup=main_menu())
            
            elif chat_id in user_data_storage:
                step = user_data_storage[chat_id]["step"]

                if step == 1:
                    user_data_storage[chat_id]["answers"]["step_1"] = text
                    user_data_storage[chat_id]["step"] = 2
                    send_message(
                        chat_id,
                        "🏃‍♂️ *Шаг 2 из 3: Активность и Здоровье*\n\n"
                        "Напишите:\n"
                        "• Тип работы и режим сна\n"
                        "• Текущие тренировки и шаги\n"
                        "• Травмы и ограничения"
                    )
                elif step == 2:
                    user_data_storage[chat_id]["answers"]["step_2"] = text
                    user_data_storage[chat_id]["step"] = 3
                    send_message(
                        chat_id,
                        "🥗 *Шаг 3 из 3: Питание и Условия*\n\n"
                        "Напишите:\n"
                        "• Где будут тренировки (зал/дом/улица) и инвентарь\n"
                        "• Приемы пищи, аллергии, бюджет"
                    )
                elif step == 3:
                    user_data_storage[chat_id]["answers"]["step_3"] = text
                    
                    # Подробная расшифровка тарифов перед выводом кнопок
                    tariffs_description = (
                        "✅ *Анкета полностью заполнена!*\n\n"
                        "Выберите подходящий формат работы:\n\n"
                        "🥉 *1. Базовый план (300 ⭐)*\n"
                        "• Что входит: На выбор только индивидуальный план питания ИЛИ только программа тренировок (для любого удобного места).\n"
                        "• Подойдет тем, кто точно знает, что именно ему нужно улучшить в первую очередь.\n\n"
                        "🥈 *2. Стандарт (500 ⭐)*\n"
                        "• Что входит: Связка «План питания + Программа тренировок» под ваши задачи.\n"
                        "• Подойдет для комплексного старта трансформации тела.\n\n"
                        "🥇 *3. VIP с ведением 2 недели (1000 ⭐)*\n"
                        "• Что входит: План питания + Тренировки + 2 недели моего личного контроля, ответов на вопросы и корректировок.\n"
                        "• Подойдет тем, кому важна поддержка на старте.\n\n"
                        "💎 *4. Месячное ведение (1500 ⭐)*\n"
                        "• Что входит: Полный фарш. План питания, регулярные тренировки, еженедельный разбор отчетов, анализ прогресса и постоянная связь со мной в течение 30 дней.\n"
                        "• Максимальный результат под ключ."
                    )
                    
                    send_message(chat_id, tariffs_description, reply_markup=payment_methods_menu())

            else:
                send_message(chat_id, "Чтобы начать, отправьте команду /start")

        self.send_response(200)
        self.end_headers()
        return
