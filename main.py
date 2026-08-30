import os
import logging
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Bot

# تنظیم لاگینگ برای عیب‌یابی در سرور
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update, context):
    await update.message.reply_text("سلام! ربات فروشگاهی هوشمند شما فعال شد.")

async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    print("🔍 BOT_TOKEN =", TOKEN)

    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN در Variables تنظیم نشده است!")

    # پاک کردن Webhook به صورت async
    bot = Bot(token=TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)

    # ساخت اپلیکیشن
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("✅ ربات با موفقیت استارت خورد...")
    await app.run_polling(allowed_updates=[])

if __name__ == '__main__':
    asyncio.run(main())
