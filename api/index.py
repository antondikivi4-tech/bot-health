import os
import json
import requests
from http.server import BaseHTTPRequestHandler

# Ваш актуальный токен бота
TOKEN = "8847126142:AAG4VExKIvX_N_h-dZ1UkvA8UvrRDMYTbNI" 
ADMIN_CHAT_ID = "673791974"

# Токен от CryptoBot подтягивается из переменных окружения Vercel (или можно вписать сюда)
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_CRYPTO_PAY")

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
            [{"text": "🥉 Базовый план ($15)", "callback_data": "pay_base"}],
            [{"text": "🥈 Стандарт ($25)", "callback_data": "pay_std"}],
            [{"text": "🥇 VIP ($50)", "callback_data": "pay_vip"}],
            [{"text": "💎 Месячное ведение ($75)", "callback_data": "pay_month"}]
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

        # Обработка нажатий на инлайн-кнопки
        if "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            data = query["data"]
            
            if data == "start_survey":
                send_message(
                    chat_id, 
                    "📋 *Шаг 1 из 3: База и Антропометрия*\n\n"
                    "Напишите следующим сообщением ваш пол, возраст, рост, вес и главную цель."
                )
            
            elif data.startswith("pay_"):
                prices = {"pay_base": 15, "pay_std": 25, "pay_vip": 50, "pay_month": 75}
                titles = {
                    "pay_base": "Базовый план ($15)", 
                    "pay_std": "Стандарт ($25)", 
                    "pay_vip": "VIP ($50)", 
                    "pay_month": "Месячное ведение ($75)"
                }
                
                amount = prices.get(data, 15)
                title = titles.get(data, "План")
                
                pay_url = create_cryptobot_invoice(amount, title, chat_id)
                if pay_url:
                    send_message(
                        chat_id, 
                        f"🔗 Ссылка на оплату тарифа *{title}*:", 
                        reply_markup={"inline_keyboard": [[{"text": f"💳 Оплатить ${amount} USDT", "url": pay_url}]]}
                    )
                else:
                    send_message(chat_id, "⚠️ Ошибка создания счета через CryptoBot. Убедитесь, что токен `CRYPTO_BOT_TOKEN` правильно указан в настройках Vercel.")

        # Обработка текстовых сообщений
        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if text == "/start":
                welcome_text = (
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок "
                    "для занятий в любом удобном месте, а также взять тебя на полное ведение.\n\n"
                    "Нажми кнопку ниже для старта анкеты:"
                )
                send_message(chat_id, welcome_text, reply_markup={"inline_keyboard": [[{"text": "🔥 Заполнить анкету", "callback_data": "start_survey"}]]})
            else:
                # Пересылаем анкету вам в админ-чат и показываем выбор тарифов
                send_message(
                    ADMIN_CHAT_ID, 
                    f"🆕 *Новый ответ от клиента (`{chat_id}`):*\n\n{text}"
                )
                
                tariffs_desc = (
                    "✅ *Анкета принята!*\n\n"
                    "Выберите подходящий формат сотрудничества:\n\n"
                    "🥉 *Базовый ($15)* — План питания ИЛИ тренировок\n"
                    "🥈 *Стандарт ($25)* — Питание + Тренировки\n"
                    "🥇 *VIP ($50)* — План + 2 недели ведения\n"
                    "💎 *Месячное ведение ($75)* — Полный контроль на 30 дней"
                )
                send_message(chat_id, tariffs_desc, reply_markup=payment_methods_menu())

        self.send_response(200)
        self.end_headers()
        return
