import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# تنظیم لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! 👋\nربات فروشگاهی هوشمند شما فعال و آماده‌ست.")

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN تنظیم نشده است!")
    if not WEBHOOK_URL:
        raise ValueError("❌ WEBHOOK_URL تنظیم نشده است!")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    logger.info("✅ ربات در حال راه‌اندازی با Webhook...")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
