import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋\nربات فروشگاهی هوشمند شما فعال و آماده‌ست.")

async def health(request):
    return web.Response(text="Bot is alive ✅", status=200)

async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data=data, bot=application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"خطا در پردازش آپدیت: {e}")
        return web.Response(status=500)

async def main():
    global application

    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    if not TOKEN or not WEBHOOK_URL:
        raise ValueError("BOT_TOKEN یا WEBHOOK_URL تنظیم نشده!")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    await application.initialize()
    await application.start()

    # تنظیم Webhook
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
    )
    logger.info("✅ Webhook تنظیم شد")

    # سرور
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"✅ سرور روی پورت {PORT} آماده است")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
