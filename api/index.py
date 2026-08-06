import os
import json
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = "ВАШ_АДМИН_CHAT_ID"  # Замените на ваш реальный Chat ID

# Временное хранилище анкет в памяти (для работы на бессерверной архитектуре)
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

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🔥 Заполнить полную анкету (Питание + Тренировки)", "callback_data": "start_survey"}],
            [{"text": "💬 Связаться с тренером", "callback_data": "contact_coach"}]
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
                    "• Тип телосложения (лишний вес, худое, атлетическое) и проблемные зоны\n"
                    "• Главная задача (похудение, набор массы, рекомпозиция, сила/выносливость)"
                )
            elif data == "contact_coach":
                send_message(chat_id, "Вы можете написать напрямую тренеру: укажите ваш вопрос, и я передам его!")

        # Текстовые сообщения от пользователя
        elif "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user = message.get("from", {})
            username = user.get("username", "нет юзернейма")
            first_name = user.get("first_name", "Клиент")

            if text == "/start":
                welcome_text = (
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок "
                    "для занятий в любом удобном месте.\n\n"
                    "Нажми кнопку ниже, чтобы начать заполнение анкеты:"
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
                        "• Тип работы (сидячая, на ногах, тяжелый физический труд) и режим сна (сколько часов спите)\n"
                        "• Текущие тренировки (вид спорта, сколько раз в неделю, длительность)\n"
                        "• Бытовая активность (шаги в день)\n"
                        "• Уровень подготовки (новичок, перерыв, регулярно)\n"
                        "• Травмы, боли (спина, колени) и хронические заболевания (давление, грыжи и т.д.)"
                    )
                elif step == 2:
                    user_data_storage[chat_id]["answers"]["step_2"] = text
                    user_data_storage[chat_id]["step"] = 3
                    send_message(
                        chat_id,
                        "🥗 *Шаг 3 из 3: Питание, Условия и Быт*\n\n"
                        "Последний блок вопросов:\n"
                        "• Где будут тренировки (зал, улица, дом) и какой доступный инвентарь (зал / гантели / без оборудования)\n"
                        "• Желаемый график тренировок (сколько дней в неделю и по сколько минут)\n"
                        "• Приемы пищи (сколько раз удобно есть: 2, 3, 5 раз)\n"
                        "• Предпочтения, аллергии (лактоза, глютен) и питьевой режим\n"
                        "• Здоровье ЖКТ и гормональный профиль\n"
                        "• Бюджет на продукты и отношения с едой (стрессовое переедание)"
                    )
                elif step == 3:
                    user_data_storage[chat_id]["answers"]["step_3"] = text
                    
                    # Собираем всю анкету целиком
                    ans = user_data_storage[chat_id]["answers"]
                    full_report = (
                        "🔔 *ПОЛНАЯ АНКЕТА КЛИЕНТА!*\n\n"
                        f"👤 Имя: {first_name} (@{username})\n"
                        f"🆔 Chat ID: `{chat_id}`\n\n"
                        f"📌 *1. База и цели:*\n{ans.get('step_1')}\n\n"
                        f"📌 *2. Активность и здоровье:*\n{ans.get('step_2')}\n\n"
                        f"📌 *3. Питание и тренировки:*\n{ans.get('step_3')}"
                    )

                    # Отправляем вам в админ-чат
                    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "ВАШ_АДМИН_CHAT_ID":
                        send_message(ADMIN_CHAT_ID, full_report)

                    # Благодарим клиента
                    send_message(
                        chat_id,
                        "✅ *Анкета успешно заполнена и отправлена тренеру!*\n\n"
                        "Спасибо за подробные ответы. Скоро я свяжусь с вами для обсуждения деталей, расчета стоимости и запуска работы!"
                    )
                    
                    # Удаляем сессию
                    del user_data_storage[chat_id]

            else:
                send_message(chat_id, "Чтобы начать заполнение анкеты, отправьте команду /start")

        self.send_response(200)
        self.end_headers()
        return
