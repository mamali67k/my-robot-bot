# main.py
import json
import logging
from telegram.ext import ApplicationBuilder, CommandHandler
import config # ایمپورت کردن توکن از فایل config

# تنظیم لاگینگ برای عیب‌یابی در سرور
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("سلام! ربات فروشگاهی هوشمند شما فعال شد.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(config.TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    print("ربات با موفقیت استارت خورد...")
    app.run_polling()
