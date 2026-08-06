import os
import json
import requests
from http.server import BaseHTTPRequestHandler

TOKEN = "8847126142:AAG4VExKIvX_N_h-dZ1UkvA8UvrRDMYTbNI" 
ADMIN_CHAT_ID = "673791974"
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN", "")

user_steps = {}

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_invoice(chat_id, title, description, amount_stars):
    url = f"https://api.telegram.org/bot{TOKEN}/sendInvoice"
    payload = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": f"stars_{chat_id}",
        "currency": "XTR",
        "prices": [{"label": "Стоимость", "amount": amount_stars}]
    }
    requests.post(url, json=payload)

def create_cryptobot_invoice(amount_usd, title, chat_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Content-Type": "application/json",
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN
    }
    payload = {
        "asset": "USDT",
        "amount": str(amount_usd),
        "description": title,
        "payload": f"user_{chat_id}",
        "allow_comments": False,
        "allow_anonymous": False
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        if data.get("ok"):
            return data["result"]["pay_url"]
    except Exception:
        pass
    return None

def payment_methods_menu(tier_key):
    return {
        "inline_keyboard": [
            [{"text": "💳 Оплатить USDT (CryptoBot)", "callback_data": f"crypto_{tier_key}"}],
            [{"text": "⭐ Оплатить Telegram Звездами", "callback_data": f"stars_{tier_key}"}]
        ]
    }

def tariffs_list_menu():
    return {
        "inline_keyboard": [
            [{"text": "🥉 Базовый ($15 / ~1125 ⭐)", "callback_data": "tier_base"}],
            [{"text": "🥈 Стандарт ($25 / ~1875 ⭐)", "callback_data": "tier_std"}],
            [{"text": "🥇 VIP ($50 / ~3750 ⭐)", "callback_data": "tier_vip"}],
            [{"text": "💎 Месячное ведение ($75 / ~5625 ⭐)", "callback_data": "tier_month"}]
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
            
            if data == "start_survey":
                user_steps[chat_id] = {"step": 1, "answers": []}
                send_message(
                    chat_id, 
                    "📋 *Шаг 1 из 3: База и Антропометрия*\n\n"
                    "Напишите ваш пол, возраст, рост, вес и главную цель."
                )
            
            elif data.startswith("tier_"):
                tier_names = {
                    "tier_base": "Базовый план ($15)",
                    "tier_std": "Стандарт ($25)",
                    "tier_vip": "VIP ($50)",
                    "tier_month": "Месячное ведение ($75)"
                }
                send_message(
                    chat_id, 
                    f"Вы выбрали тариф: *{tier_names.get(data, 'План')}*\n\nВыберите удобный способ оплаты:", 
                    reply_markup=payment_methods_menu(data)
                )

            elif data.startswith("crypto_"):
                tier = data.replace("crypto_", "")
                prices = {"tier_base": 15, "tier_std": 25, "tier_vip": 50, "tier_month": 75}
                titles = {"tier_base": "Базовый план ($15)", "tier_std": "Стандарт ($25)", "tier_vip": "VIP ($50)", "tier_month": "Месячное ведение ($75)"}
                
                amount = prices.get(tier, 15)
                title = titles.get(tier, "План")
                
                pay_url = create_cryptobot_invoice(amount, title, chat_id)
                if pay_url:
                    send_message(chat_id, f"🔗 Ссылка на оплату тарифа *{title}*:", reply_markup={"inline_keyboard": [[{"text": f"💳 Оплатить ${amount} USDT", "url": pay_url}]]})
                else:
                    send_message(chat_id, f"💳 Оплата тарифа *{title}* (${amount} USDT)\n\nПожалуйста, переведите средства через бот [@CryptoBot](https://t.me/CryptoBot) и отправьте скриншот сюда.")

            elif data.startswith("stars_"):
                tier = data.replace("stars_", "")
                # Скорректированный курс звезд с учетом комиссии магазинов приложений
                star_prices = {"tier_base": 1125, "tier_std": 1875, "tier_vip": 3750, "tier_month": 5625}
                titles = {"tier_base": "Базовый план", "tier_std": "Стандарт", "tier_vip": "VIP", "tier_month": "Месячное ведение"}
                
                stars_amount = star_prices.get(tier, 1125)
                title_text = titles.get(tier, "План")
                
                send_invoice(
                    chat_id, 
                    title=f"Тариф: {title_text}", 
                    description="Оплата индивидуальной программы питания и тренировок", 
                    amount_stars=stars_amount
                )

        elif "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if "successful_payment" in msg:
                send_message(ADMIN_CHAT_ID, f"💰 *Успешная оплата Звездами (XTR) от клиента* `{chat_id}`!")
                send_message(chat_id, "🎉 Спасибо за оплату! Ваша покупка успешно подтверждена. Скоро я свяжусь с вами для работы.")
                return

            if text == "/start":
                user_steps[chat_id] = {"step": 0, "answers": []}
                send_message(
                    chat_id, 
                    "Привет! 👋 Я помогу составить индивидуальный план питания и программу тренировок.\n\nНажми кнопку ниже для старта анкеты:", 
                    reply_markup={"inline_keyboard": [[{"text": "🔥 Заполнить анкету", "callback_data": "start_survey"}]]}
                )
            elif chat_id in user_steps:
                current_step = user_steps[chat_id]["step"]
                user_steps[chat_id]["answers"].append(text)

                if current_step == 1:
                    user_steps[chat_id]["step"] = 2
                    send_message(
                        chat_id, 
                        "🏃‍♂️ *Шаг 2 из 3: Активность и Здоровье*\n\n"
                        "Напишите ваш режим дня, уровень активности и наличие травм."
                    )
                elif current_step == 2:
                    user_steps[chat_id]["step"] = 3
                    send_message(
                        chat_id, 
                        "🥗 *Шаг 3 из 3: Питание и Условия*\n\n"
                        "Напишите где будут тренировки (зал/дом) и ваши предпочтения в еде."
                    )
                elif current_step >= 3:
                    answers = user_steps[chat_id]["answers"]
                    report = (
                        f"🆕 *Новая анкета от клиента (`{chat_id}`):*\n\n"
                        f"📌 *Шаг 1:* {answers[0]}\n"
                        f"📌 *Шаг 2:* {answers[1]}\n"
                        f"📌 *Шаг 3:* {answers[2]}"
                    )
                    send_message(ADMIN_CHAT_ID, report)
                    
                    send_message(
                        chat_id, 
                        "✅ *Анкета полностью заполнена!*\n\nВыберите подходящий тариф:", 
                        reply_markup=tariffs_list_menu()
                    )
                    del user_steps[chat_id]

        self.send_response(200)
        self.end_headers()
        return
