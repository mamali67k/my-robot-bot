import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

# تنظیم لاگینگ برای عیب‌یابی در سرور
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update, context):
    await update.message.reply_text("سلام! ربات فروشگاهی هوشمند شما فعال شد.")

if __name__ == '__main__':
    # خواندن توکن از Environment Variable در Railway
    TOKEN = os.getenv("BOT_TOKEN")

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN در Variables تنظیم نشده است!")

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    print("✅ ربات با موفقیت استارت خورد...")
    app.run_polling()
