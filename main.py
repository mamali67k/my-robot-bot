import os
import logging
from telegram.ext import Application, CommandHandler

# تنظیم لاگینگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update, context):
    await update.message.reply_text("سلام! ربات فروشگاهی هوشمند شما فعال شد.")

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN در Variables تنظیم نشده است!")

    # ساخت اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلر
    application.add_handler(CommandHandler("start", start))

    print("✅ ربات با موفقیت استارت خورد...")
    
    # این خط هم webhook رو پاک می‌کنه و هم polling رو شروع می‌کنه
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
