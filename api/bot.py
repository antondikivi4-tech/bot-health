import os
import asyncio
from http.server import BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await bot.send_message(message.chat.id, "Бот на Vercel работает! 🚀")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        asyncio.run(self.handle_update(body))
        self.send_response(200)
        self.end_headers()

    async def handle_update(self, body):
        update = Update.model_validate_json(body)
        await dp.feed_update(bot, update)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online")
