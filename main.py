import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------- داده‌های محصولات ----------------------
CATEGORIES = {
    "mobile": {
        "name": "📱 موبایل و لوازم جانبی",
        "products": [
            {
                "id": "p1",
                "name": "گوشی سامسونگ A55",
                "price": 28500000,
                "description": "گوشی سامسونگ گلکسی A55 با حافظه ۲۵۶ گیگابایت و رم ۸ گیگ",
                "photo": None
            },
            {
                "id": "p2",
                "name": "ایرپاد پرو ۲",
                "price": 12500000,
                "description": "ایرپاد پرو نسل دوم اپل با قابلیت حذف نویز فعال",
                "photo": None
            }
        ]
    },
    "laptop": {
        "name": "💻 لپ‌تاپ و کامپیوتر",
        "products": [
            {
                "id": "p3",
                "name": "لپ‌تاپ لنوو IdeaPad",
                "price": 42000000,
                "description": "لپ‌تاپ لنوو با پردازنده Core i7 و ۱۶ گیگ رم",
                "photo": None
            }
        ]
    },
    "home": {
        "name": "🏠 لوازم خانگی",
        "products": []
    }
}

WELCOME_TEXT = """
سلام به ربات فروشگاهی ما خوش آمدید! 👋

از منوی زیر می‌توانید بخش مورد نظر خود را انتخاب کنید.
"""

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛍 دسته‌بندی محصولات", callback_data="categories")],
        [InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback")],
        [InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")],
        [InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())

async def show_categories(query):
    text = "🛍 لطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:"
    keyboard = []
    for cat_id, cat_data in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_products(query, category_id: str):
    category = CATEGORIES.get(category_id)
    if not category:
        await query.edit_message_text("❌ دسته‌بندی یافت نشد.")
        return

    if not category["products"]:
        text = f"در حال حاضر محصولی در دسته‌بندی «{category['name']}» وجود ندارد."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="categories")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = f"محصولات دسته‌بندی «{category['name']}»:\n\n"
    keyboard = []
    for product in category["products"]:
        price_text = f"{product['price']:,} تومان"
        button_text = f"{product['name']} | {price_text}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"product_{product['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="categories")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_product_detail(query, product_id: str):
    product = None
    for cat in CATEGORIES.values():
        for p in cat["products"]:
            if p["id"] == product_id:
                product = p
                break
        if product:
            break

    if not product:
        await query.edit_message_text("❌ محصول یافت نشد.")
        return

    text = f"""
🛍 **{product['name']}**

💰 قیمت: {product['price']:,} تومان

📝 توضیحات:
{product['description']}
"""
    keyboard = [
        [InlineKeyboardButton("🛒 افزودن به سبد خرید", callback_data=f"addcart_{product_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="categories")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "categories":
        await show_categories(query)
    elif data.startswith("category_"):
        await show_products(query, data.replace("category_", ""))
    elif data.startswith("product_"):
        await show_product_detail(query, data.replace("product_", ""))
    elif data == "feedback":
        text = "📝 لطفاً نقد یا پیشنهاد خود را بنویسید و ارسال کنید."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "club":
        text = "⭐ به باشگاه مشتریان خوش آمدید!\n\nامتیاز فعلی شما: ۰"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "about":
        text = "ℹ️ این ربات فروشگاهی با هدف ارائه بهترین محصولات طراحی شده است."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "back_main":
        await query.edit_message_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())
    elif data.startswith("addcart_"):
        await query.answer("محصول به سبد خرید اضافه شد (به زودی کامل می‌شود)", show_alert=True)

async def health(request):
    return web.Response(text="Bot is alive ✅", status=200)

async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.exception("خطا در webhook:")
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
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()

    # تنظیم مجدد Webhook
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info("✅ Webhook با موفقیت تنظیم شد")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"✅ سرور آماده است روی پورت {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
