import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# تنظیمات ادمین
# ============================================================
def get_admin_ids():
    raw = os.getenv("ADMIN_IDS", "1190530645")
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        return []

ADMIN_IDS = get_admin_ids()

# ============================================================
# مدیریت داده‌های کاربران (JSON)
# ============================================================
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"خطا در خواندن فایل کاربران: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در ذخیره فایل کاربران: {e}")

def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    users = load_users()
    user_id_str = str(user_id)

    if user_id_str not in users:
        users[user_id_str] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "phone": None,
            "address": None,
            "level": 3,  # 3=عادی | 2=علاقه‌مند | 1=بالقوه | vip
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "categories_viewed": []
        }
        save_users(users)
        logger.info(f"کاربر جدید ثبت شد: {user_id}")
    else:
        # آپدیت آخرین بازدید
        users[user_id_str]["last_seen"] = datetime.now().isoformat()
        if username:
            users[user_id_str]["username"] = username
        save_users(users)

    return users[user_id_str]

def upgrade_user_level(user_id: int, new_level):
    """ارتقای سطح کاربر (فقط به سمت بالاتر)"""
    users = load_users()
    user_id_str = str(user_id)

    if user_id_str not in users:
        return

    current = users[user_id_str]["level"]

    # ترتیب اولویت: 3 < 2 < 1 < vip
    level_order = {3: 0, 2: 1, 1: 2, "vip": 3}

    if level_order.get(new_level, -1) > level_order.get(current, -1):
        users[user_id_str]["level"] = new_level
        save_users(users)
        logger.info(f"سطح کاربر {user_id} به {new_level} ارتقا یافت")

def add_category_viewed(user_id: int, category_id: str):
    users = load_users()
    user_id_str = str(user_id)

    if user_id_str not in users:
        return

    if category_id not in users[user_id_str]["categories_viewed"]:
        users[user_id_str]["categories_viewed"].append(category_id)
        save_users(users)

def get_stats():
    users = load_users()
    stats = {
        "total": len(users),
        "level_3": 0,
        "level_2": 0,
        "level_1": 0,
        "vip": 0
    }

    for user in users.values():
        level = user.get("level", 3)
        if level == 3:
            stats["level_3"] += 1
        elif level == 2:
            stats["level_2"] += 1
        elif level == 1:
            stats["level_1"] += 1
        elif level == "vip":
            stats["vip"] += 1

    return stats

# ============================================================
# داده‌های محصولات
# ============================================================
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

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def main_menu_keyboard():
    keyboard = []
    cat_items = list(CATEGORIES.items())
    for i in range(0, len(cat_items), 2):
        row = []
        cat_id, cat_data = cat_items[i]
        row.append(InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}"))
        if i + 1 < len(cat_items):
            cat_id2, cat_data2 = cat_items[i + 1]
            row.append(InlineKeyboardButton(cat_data2["name"], callback_data=f"category_{cat_id2}"))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback"),
        InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")
    ])
    keyboard.append([InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ افزودن دسته‌بندی", callback_data="admin_add_category")],
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="admin_manage_products")],
        [InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data="admin_manage_admins")],
        [InlineKeyboardButton("📊 آمار مشتریان", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون یوزرنیم"

    if not is_admin(user_id):
        logger.warning(f"تلاش غیرمجاز برای پنل ادمین | {user_id} | @{username}")
        await update.message.reply_text("دستور نامعتبر است.")
        return

    text = "🛠️ **پنل مدیریت ربات**\n\nاز منوی زیر بخش مورد نظر را انتخاب کنید."
    await update.message.reply_text(text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown")

async def show_products(query, category_id: str):
    # ارتقای سطح به ۲ (علاقه‌مند)
    user_id = query.from_user.id
    upgrade_user_level(user_id, 2)
    add_category_viewed(user_id, category_id)

    category = CATEGORIES.get(category_id)
    if not category:
        await query.edit_message_text("❌ دسته‌بندی یافت نشد.")
        return

    if not category["products"]:
        text = f"در حال حاضر محصولی در دسته‌بندی «{category['name']}» وجود ندارد."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = f"محصولات دسته‌بندی «{category['name']}»:\n\n"
    keyboard = []
    for product in category["products"]:
        price_text = f"{product['price']:,} تومان"
        button_text = f"{product['name']} | {price_text}"
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"product_{category_id}_{product['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_main")])
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_product_detail(query, category_id: str, product_id: str):
    category = CATEGORIES.get(category_id)
    if not category:
        await query.edit_message_text("❌ دسته‌بندی یافت نشد.")
        return

    product = next((p for p in category["products"] if p["id"] == product_id), None)
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
        [InlineKeyboardButton("🔙 بازگشت به محصولات", callback_data=f"category_{category_id}")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_stats(query):
    stats = get_stats()
    text = f"""
📊 **آمار مشتریان ربات**

👥 کل کاربران: {stats['total']}

🔹 مشتری عادی (سطح ۳): {stats['level_3']}
🔸 مشتری علاقه‌مند (سطح ۲): {stats['level_2']}
🔶 مشتری بالقوه (سطح ۱): {stats['level_1']}
⭐ مشتری VIP: {stats['vip']}
"""
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_back")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("category_"):
        category_id = data.replace("category_", "")
        await show_products(query, category_id)

    elif data.startswith("product_"):
        parts = data.split("_")
        if len(parts) == 3:
            await show_product_detail(query, parts[1], parts[2])

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

    # بخش ادمین
    elif data.startswith("admin_") or data == "admin_back":
        if not is_admin(user_id):
            logger.warning(f"تلاش غیرمجاز ادمین | {user_id}")
            await query.answer("دسترسی غیرمجاز", show_alert=True)
            return

        if data == "admin_stats" or data == "admin_back":
            if data == "admin_stats":
                await show_stats(query)
            else:
                await query.edit_message_text(
                    "🛠️ **پنل مدیریت ربات**\n\nاز منوی زیر بخش مورد نظر را انتخاب کنید.",
                    reply_markup=admin_menu_keyboard(),
                    parse_mode="Markdown"
                )
        elif data == "admin_add_category":
            await query.edit_message_text("➕ بخش افزودن دسته‌بندی به زودی فعال می‌شود.", reply_markup=admin_menu_keyboard())
        elif data == "admin_manage_products":
            await query.edit_message_text("📦 بخش مدیریت محصولات به زودی فعال می‌شود.", reply_markup=admin_menu_keyboard())
        elif data == "admin_manage_admins":
            await query.edit_message_text("👥 بخش مدیریت ادمین‌ها به زودی فعال می‌شود.", reply_markup=admin_menu_keyboard())

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
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()

    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info("✅ Webhook تنظیم شد")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"✅ سرور آماده است")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
