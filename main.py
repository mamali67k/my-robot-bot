import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from aiohttp import web

# ---------------------- تنظیمات لاگ ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------- هندلر استارت ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋\nربات فروشگاهی هوشمند شما فعال و آماده‌ست.")

# ---------------------- هندلر بیدار باش (Keep Alive) ----------------------
async def keep_alive(request):
    return web.Response(text="ربات زنده‌ست ✅", status=200)

# ---------------------- تابع اصلی ----------------------
async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://xxx.up.railway.app
    PORT = int(os.getenv("PORT", 8080))

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN تنظیم نشده است!")
    if not WEBHOOK_URL:
        raise ValueError("❌ WEBHOOK_URL تنظیم نشده است!")

    # ساخت اپلیکیشن
    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))

    # راه‌اندازی سرور aiohttp برای Webhook + Keep Alive
    app = web.Application()
    app.router.add_get("/", keep_alive)          # برای بیدار نگه داشتن
    app.router.add_get("/health", keep_alive)    # مسیر اضافی
    app.router.add_post("/webhook", application.telegram_update_handler)  # مسیر Webhook

    # تنظیم Webhook در تلگرام
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
    )

    logger.info("✅ ربات با موفقیت استارت خورد و Webhook تنظیم شد...")

    # اجرای سرور
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # نگه داشتن برنامه زنده
    await asyncio.Event().wait()

# ---------------------- اجرا ----------------------
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
