import os
import asyncio
import aiosqlite
from aiohttp import web
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv
from yookassa import Configuration, Payment

from database import DB_FILE, init_db, add_balance, get_balance, save_payment

load_dotenv("/opt/bots/numerium_bot/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY


async def init_payments_table():
    await init_db()


async def payment_already_processed(payment_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            "SELECT payment_id FROM processed_payments WHERE payment_id = ?",
            (payment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def mark_payment_processed(payment_id, user_id, count):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO processed_payments (payment_id, user_id, count) VALUES (?, ?, ?)",
            (payment_id, user_id, count)
        )
        await db.commit()


async def verify_yookassa_payment(payment_id, user_id, count, amount_rub):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        print("YooKassa credentials are empty", flush=True)
        return False

    try:
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
    except Exception as e:
        print(f"YooKassa payment verification error: {e}", flush=True)
        return False

    metadata = payment.metadata or {}

    try:
        real_user_id = int(metadata.get("user_id"))
        real_count = int(metadata.get("count"))
        real_amount = float(payment.amount.value)
    except (TypeError, ValueError):
        print("YooKassa payment verification failed: bad metadata", flush=True)
        return False

    if payment.status != "succeeded":
        print(f"YooKassa payment verification failed: status={payment.status}", flush=True)
        return False

    if not payment.paid:
        print("YooKassa payment verification failed: paid is false", flush=True)
        return False

    if real_user_id != user_id or real_count != count:
        print("YooKassa payment verification failed: metadata mismatch", flush=True)
        return False

    if abs(real_amount - amount_rub) > 0.01:
        print("YooKassa payment verification failed: amount mismatch", flush=True)
        return False

    return True


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
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)

    event = data.get("event")
    obj = data.get("object", {})

    if event != "payment.succeeded":
        return web.json_response({"ok": True})

    payment_id = obj.get("id")
    metadata = obj.get("metadata") or {}

    try:
        user_id = int(metadata.get("user_id"))
        count = int(metadata.get("count"))
        amount_rub = float((obj.get("amount") or {}).get("value", 0))
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "bad_metadata"}, status=400)

    if not payment_id:
        return web.json_response({"ok": False, "error": "missing_payment_id"}, status=400)

    if await payment_already_processed(payment_id):
        return web.json_response({"ok": True, "status": "already_processed"})

    if not await verify_yookassa_payment(payment_id, user_id, count, amount_rub):
        return web.json_response({"ok": False, "error": "payment_verification_failed"}, status=403)

    await add_balance(user_id, count)
    await mark_payment_processed(payment_id, user_id, count)
    await save_payment(payment_id, user_id, amount_rub, count)

    balance = await get_balance(user_id)

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


async def on_startup(app):
    await init_payments_table()


app = web.Application()
app.on_startup.append(on_startup)
app.router.add_get("/health", health)
app.router.add_post("/yookassa/webhook", yookassa_webhook)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8083)
