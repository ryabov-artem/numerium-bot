import os
import sqlite3
import aiohttp
from aiohttp import web
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from database import add_balance, get_balance, save_payment

load_dotenv("/opt/bots/numerium_bot/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
DB_FILE = "/opt/bots/numerium_bot/data/database.db"


def init_payments_table():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS processed_payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            count INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def payment_already_processed(payment_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT payment_id FROM processed_payments WHERE payment_id = ?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def mark_payment_processed(payment_id, user_id, count):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO processed_payments (payment_id, user_id, count) VALUES (?, ?, ?)",
        (payment_id, user_id, count)
    )
    conn.commit()
    conn.close()


async def send_telegram_message(user_id, text):
    if not BOT_TOKEN:
        print("BOT_TOKEN is empty", flush=True)
        return

    try:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
        await bot.send_message(chat_id=user_id, text=text)
        await bot.session.close()
        print(f"Telegram notification sent to {user_id}", flush=True)
    except Exception as e:
        print(f"Telegram sendMessage error: {e}", flush=True)


async def yookassa_webhook(request):
    data = await request.json()

    event = data.get("event")
    obj = data.get("object", {})

    if event != "payment.succeeded":
        return web.json_response({"ok": True})

    payment_id = obj.get("id")
    metadata = obj.get("metadata") or {}

    user_id = int(metadata.get("user_id"))
    count = int(metadata.get("count"))
    amount_rub = float((obj.get("amount") or {}).get("value", 0))

    if payment_already_processed(payment_id):
        return web.json_response({"ok": True, "status": "already_processed"})

    add_balance(user_id, count)
    mark_payment_processed(payment_id, user_id, count)
    save_payment(payment_id, user_id, amount_rub, count)

    balance = get_balance(user_id)

    await send_telegram_message(
        user_id,
        f"🎉 Оплата успешно получена\n\n"
        f"💎 На баланс зачислено: {count} разбор(ов)\n"
        f"🔢 Текущий баланс: {balance} разбор(ов)\n\n"
        f"Спасибо за использование Нумериума.\n\n"
        f"✨ Теперь можно выбрать любой нумерологический анализ:\n"
        f"• Число судьбы\n"
        f"• Число жизненного пути\n"
        f"• Совместимость\n"
        f"• Личные качества\n"
        f"• Предназначение"
    )

    return web.json_response({"ok": True})


async def health(request):
    return web.Response(text="OK")


app = web.Application()
app.router.add_get("/health", health)
app.router.add_post("/yookassa/webhook", yookassa_webhook)

if __name__ == "__main__":
    init_payments_table()
    web.run_app(app, host="127.0.0.1", port=8083)
