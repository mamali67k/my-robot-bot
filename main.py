import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
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

async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    if not TOKEN or not WEBHOOK_URL:
        raise ValueError("BOT_TOKEN یا WEBHOOK_URL تنظیم نشده است!")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    # ساخت سرور aiohttp
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", application.bot.update_handler)  # مسیر وب‌هوک

    # تنظیم Webhook در تلگرام
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
    )

    logger.info("✅ ربات با موفقیت بالا آمد")

    # اجرای سرور
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # نگه داشتن برنامه
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
