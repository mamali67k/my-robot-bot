import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from aiohttp import web

# ---------------------- تنظیم لاگ ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------- متن‌های ثابت ----------------------
WELCOME_TEXT = """
سلام به ربات فروشگاهی ما خوش آمدید! 👋

از منوی زیر می‌توانید بخش مورد نظر خود را انتخاب کنید.
"""

# ---------------------- منوی اصلی ----------------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛍 دسته‌بندی محصولات", callback_data="categories")],
        [InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback")],
        [InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------------- دستور /start ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard()
    )

# ---------------------- مدیریت دکمه‌های اینلاین ----------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "categories":
        text = "🛍 لطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("📱 موبایل و لوازم جانبی", callback_data="cat_mobile")],
            [InlineKeyboardButton("💻 لپ‌تاپ و کامپیوتر", callback_data="cat_laptop")],
            [InlineKeyboardButton("🏠 لوازم خانگی", callback_data="cat_home")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")],
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "feedback":
        text = "📝 لطفاً نقد، پیشنهاد یا نظر خود را بنویسید و ارسال کنید.\n\nپیام شما برای مدیریت ارسال خواهد شد."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        # در مرحله بعد سیستم دریافت پیام کاربر را اضافه می‌کنیم

    elif data == "club":
        text = """
⭐ به باشگاه مشتریان خوش آمدید!

با خرید از ما امتیاز جمع کنید و از تخفیف‌های ویژه بهره‌مند شوید.

امتیاز فعلی شما: ۰
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "about":
        text = "ℹ️ این ربات فروشگاهی با هدف ارائه بهترین محصولات و خدمات طراحی شده است."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_main":
        await query.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("cat_"):
        category_name = {
            "cat_mobile": "موبایل و لوازم جانبی",
            "cat_laptop": "لپ‌تاپ و کامپیوتر",
            "cat_home": "لوازم خانگی"
        }.get(data, "دسته‌بندی")
        
        text = f"محصولات دسته‌بندی «{category_name}» به زودی اضافه می‌شوند."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="categories")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------- مسیر سلامت ----------------------
async def health(request):
    return web.Response(text="Bot is alive ✅", status=200)

# ---------------------- مسیر Webhook ----------------------
async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data=data, bot=application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"خطا در پردازش آپدیت: {e}")
        return web.Response(status=500)

# ---------------------- تابع اصلی ----------------------
async def main():
    global application

    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    if not TOKEN or not WEBHOOK_URL:
        raise ValueError("BOT_TOKEN یا WEBHOOK_URL تنظیم نشده!")

    application = Application.builder().token(TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()

    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
    )
    logger.info("✅ Webhook تنظیم شد")

    # سرور aiohttp
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
