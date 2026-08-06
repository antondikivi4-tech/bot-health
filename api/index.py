import os
import json
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = "619019:AAuGdlOvomBm5dWuv3nE11Fd5qdiBQQgGWA" 
ADMIN_CHAT_ID = "673791974"
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_CRYPTO_PAY")

# Хранилище (в реальном проекте на Vercel лучше дублировать шаги через стейт, но для теста сделаем стабильнее)
user_data_storage = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def create_cryptobot_invoice(amount_usd, title, chat_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {
        "asset": "USDT",
        "amount": str(amount_usd),
        "description": title,
        "payload": f"user_{chat_id}"
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        if data.get("ok"):
            return data["result"]["pay_url"]
    except Exception:
        pass
    return None

def payment_methods_menu():
    return {
        "inline_keyboard": [
            [{"text": "🥉 Базовый ($15)", "callback_data": "crypto_base"}],
            [{"text": "🥈 Стандарт ($25)", "callback_data": "crypto_std"}],
            [{"text": "🥇 VIP ($50)", "callback_data": "crypto_vip"}],
            [{"text": "💎 Месячное ведение ($75)", "callback_data": "crypto_month"}]
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

        if "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            data = query["data"]
            
            prices = {"crypto_base": 15, "crypto_std": 25, "crypto_vip": 50, "crypto_month": 75}
            titles = {
                "crypto_base": "Базовый план ($15)", 
                "crypto_std": "Стандарт ($25)", 
                "crypto_vip": "VIP ($50)", 
                "crypto_month": "Месячное ведение ($75)"
            }

            if data == "start_survey":
                user_data_storage[chat_id] = {"step": 1, "answers": {}}
                send_message(
                    chat_id, 
                    "📋 *Шаг 1 из 3: База и Антропометрия*\n\n"
                    "Напишите одним сообщением:\n"
                    "• Пол, возраст, рост и вес\n"
                    "• Цель (похудение/масса)"
                )
            elif data in prices:
                pay_url = create_cryptobot_invoice(prices[data], titles[data], chat_id)
                if pay_url:
                    send_message(
                        chat_id, 
                        f"🔗 Ссылка на оплату тарифа *{titles[data]}*:", 
                        reply_markup={"inline_keyboard": [[{"text": f"💳 Оплатить ${prices[data]} USDT", "url": pay_url}]]}
                    )
                else:
                    send_message(chat_id, "Ошибка создания счета через CryptoBot. Проверьте токен в настройках Vercel.")

        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                user_data_storage[chat_id] = {"step": 0, "answers": {}}
                welcome_text = (
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок.\n\n"
                    "Нажми кнопку ниже для старта:"
                )
                send_message(chat_id, welcome_text, reply_markup={"inline_keyboard": [[{"text": "🔥 Заполнить анкету", "callback_data": "start_survey"}]]})
            
            else:
                # Если пользователь прислал текст, а сессии нет — инициализируем ее автоматически
                if chat_id not in user_data_storage:
                    user_data_storage[chat_id] = {"step": 1, "answers": {}}

                step = user_data_storage[chat_id]["step"]

                if step == 1:
                    user_data_storage[chat_id]["answers"]["step_1"] = text
                    user_data_storage[chat_id]["step"] = 2
                    send_message(
                        chat_id, 
                        "🏃‍♂️ *Шаг 2 из 3: Активность и Здоровье*\n\n"
                        "Напишите:\n"
                        "• Режим дня и шаги\n"
                        "• Травмы или ограничения"
                    )
                elif step == 2:
                    user_data_storage[chat_id]["answers"]["step_2"] = text
                    user_data_storage[chat_id]["step"] = 3
                    send_message(
                        chat_id, 
                        "🥗 *Шаг 3 из 3: Питание и Условия*\n\n"
                        "Напишите:\n"
                        "• Где будут тренировки (зал/дом)\n"
                        "• Аллергии и предпочтения в еде"
                    )
                elif step >= 3:
                    user_data_storage[chat_id]["answers"]["step_3"] = text
                    
                    ans = user_data_storage[chat_id]["answers"]
                    report = (
                        "🆕 *Новая завершенная анкета!*\n\n"
                        f"👤 От: ` {chat_id} `\n\n"
                        f"📌 *Шаг 1:* {ans.get('step_1')}\n\n"
                        f"📌 *Шаг 2:* {ans.get('step_2')}\n\n"
                        f"📌 *Шаг 3:* {ans.get('step_3')}"
                    )
                    send_message(ADMIN_CHAT_ID, report)
                    
                    send_message(
                        chat_id, 
                        "✅ *Анкета полностью заполнена!*\n\nВыберите подходящий тариф для оплаты:", 
                        reply_markup=payment_methods_menu()
                    )
                    
                    # Сбрасываем сессию
                    del user_data_storage[chat_id]

        self.send_response(200)
        self.end_headers()
        return
