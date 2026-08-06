import os
import json
from http.server import BaseHTTPRequestHandler
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data.decode('utf-8'))

            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                
                # Ответ на сообщение пользователя
                if text == "/start":
                    reply_text = "Привет! Бот на Vercel успешно работает! 🚀"
                else:
                    reply_text = f"Я получил твое сообщение: {text}"

                send_url = f"{TELEGRAM_API_URL}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": reply_text
                }
                requests.post(send_url, json=payload)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Telegram Bot is online on Vercel!")
