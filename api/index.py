import os
import json
import requests
from http.server import BaseHTTPRequestHandler

# Основной токен вашего бота
TOKEN = "619019:AAuGdlOvomBm5dWuv3nE11Fd5qdiBQQgGWA" 
# Ваш ID для получения уведомлений
ADMIN_CHAT_ID = "673791974"
# Токен от CryptoBot (Crypto Pay API Token)
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_CRYPTO_PAY")

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
            titles = {"crypto_base": "Базовый план", "crypto_std": "Стандарт", "crypto_vip": "VIP", "crypto_month": "Месячное ведение"}

            if data == "start_survey":
                user_data_storage[chat_id] = {"step": 1, "answers": {}}
                send_message(chat_id, "📋 *Шаг 1: Напишите ваши данные (пол, возраст, рост, вес, цель).*")
            elif data in prices:
                pay_url = create_cryptobot_invoice(prices[data], titles[data], chat_id)
                if pay_url:
                    send_message(chat_id, f"🔗 Ссылка на оплату *{titles[data]}*:", reply_markup={"inline_keyboard": [[{"text": f"💳 Оплатить ${prices[data]}", "url": pay_url}]]})
                else:
                    send_message(chat_id, "Ошибка связи с платежной системой.")

        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                send_message(chat_id, "Привет! Заполним анкету?", reply_markup={"inline_keyboard": [[{"text": "Начать", "callback_data": "start_survey"}]]})
            elif chat_id in user_data_storage:
                step = user_data_storage[chat_id]["step"]
                user_data_storage[chat_id]["answers"][f"step_{step}"] = text
                
                if step < 3:
                    user_data_storage[chat_id]["step"] += 1
                    send_message(chat_id, f"✅ Принято! *Шаг {user_data_storage[chat_id]['step']}* — напишите ответ.")
                else:
                    send_message(chat_id, "✅ Анкета готова! Выберите тариф:", reply_markup=payment_methods_menu())
                    # Отправка анкеты админу
                    send_message(ADMIN_CHAT_ID, f"🆕 Новая анкета:\n{user_data_storage[chat_id]['answers']}")

        self.send_response(200)
        self.end_headers()
        return
