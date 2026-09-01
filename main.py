import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# تنظیمات
# ============================================================
def get_admin_ids():
    raw = os.getenv("ADMIN_IDS", "1190530645")
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        return []

ADMIN_IDS = get_admin_ids()

USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"

# ============================================================
# مدیریت کاربران
# ============================================================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_or_create_user(user_id, username=None, full_name=None):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "phone": None,
            "address": None,
            "level": 3,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "categories_viewed": []
        }
        save_users(users)
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        if username:
            users[uid]["username"] = username
        save_users(users)
    return users[uid]

def upgrade_user_level(user_id, new_level):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        return
    order = {3: 0, 2: 1, 1: 2, "vip": 3}
    current = users[uid]["level"]
    if order.get(new_level, -1) > order.get(current, -1):
        users[uid]["level"] = new_level
        save_users(users)

def add_category_viewed(user_id, category_id):
    users = load_users()
    uid = str(user_id)
    if uid in users and category_id not in users[uid]["categories_viewed"]:
        users[uid]["categories_viewed"].append(category_id)
        save_users(users)

def get_stats():
    users = load_users()
    stats = {"total": len(users), "level_3": 0, "level_2": 0, "level_1": 0, "vip": 0}
    for u in users.values():
        lvl = u.get("level", 3)
        if lvl == 3: stats["level_3"] += 1
        elif lvl == 2: stats["level_2"] += 1
        elif lvl == 1: stats["level_1"] += 1
        elif lvl == "vip": stats["vip"] += 1
    return stats

# ============================================================
# مدیریت محصولات
# ============================================================
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        default = {
            "categories": {
                "mobile": {
                    "name": "📱 موبایل و لوازم جانبی",
                    "parent": None,
                    "products": []
                },
                "laptop": {
                    "name": "💻 لپ‌تاپ و کامپیوتر",
                    "parent": None,
                    "products": []
                },
                "home": {
                    "name": "🏠 لوازم خانگی",
                    "parent": None,
                    "products": []
                }
            }
        }
        save_products(default)
        return default
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"categories": {}}

def save_products(data):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_categories():
    return load_products().get("categories", {})

# ============================================================
# کیبوردها
# ============================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_menu_keyboard():
    cats = get_categories()
    keyboard = []
    items = list(cats.items())
    for i in range(0, len(items), 2):
        row = []
        cid, cdata = items[i]
        row.append(InlineKeyboardButton(cdata["name"], callback_data=f"category_{cid}"))
        if i + 1 < len(items):
            cid2, cdata2 = items[i + 1]
            row.append(InlineKeyboardButton(cdata2["name"], callback_data=f"category_{cid2}"))
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback"),
        InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")
    ])
    keyboard.append([InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن دسته‌بندی", callback_data="admin_add_category")],
        [InlineKeyboardButton("🛒 افزودن محصول", callback_data="admin_add_product")],
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="admin_manage_products")],
        [InlineKeyboardButton("📊 آمار مشتریان", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ])

def choose_category_keyboard():
    cats = get_categories()
    keyboard = []
    for cid, cdata in cats.items():
        keyboard.append([InlineKeyboardButton(cdata["name"], callback_data=f"addprod_cat_{cid}")])
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# هندلرها
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        "سلام به ربات فروشگاهی ما خوش آمدید! 👋\n\nاز منوی زیر انتخاب کنید:",
        reply_markup=main_menu_keyboard()
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("دستور نامعتبر است.")
        return
    context.user_data.clear()
    await update.message.reply_text(
        "🛠️ **پنل مدیریت**",
        reply_markup=admin_menu_keyboard(),
        parse_mode="Markdown"
    )

async def show_products(query, category_id):
    user_id = query.from_user.id
    upgrade_user_level(user_id, 2)
    add_category_viewed(user_id, category_id)

    cats = get_categories()
    category = cats.get(category_id)
    if not category:
        await query.edit_message_text("دسته‌بندی یافت نشد.")
        return

    products = category.get("products", [])
    if not products:
        text = f"محصولی در «{category['name']}» وجود ندارد."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = f"محصولات «{category['name']}»:\n\n"
    keyboard = []
    for p in products:
        btn = f"{p['name']} | {p['price']:,} تومان"
        keyboard.append([InlineKeyboardButton(btn, callback_data=f"product_{category_id}_{p['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_product_detail(query, category_id, product_id):
    cats = get_categories()
    category = cats.get(category_id)
    if not category:
        await query.edit_message_text("یافت نشد.")
        return
    product = next((p for p in category["products"] if p["id"] == product_id), None)
    if not product:
        await query.edit_message_text("محصول یافت نشد.")
        return

    text = f"""
🛍 **{product['name']}**

💰 قیمت: {product['price']:,} تومان

📝 {product['description']}
"""
    keyboard = [
        [InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"addcart_{product_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"category_{category_id}")]
    ]

    if product.get("photo"):
        await query.message.reply_photo(
            photo=product["photo"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await query.delete_message()
    else:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_stats(query):
    stats = get_stats()
    text = f"""
📊 **آمار مشتریان**

👥 کل: {stats['total']}
🔹 عادی (۳): {stats['level_3']}
🔸 علاقه‌مند (۲): {stats['level_2']}
🔶 بالقوه (۱): {stats['level_1']}
⭐ VIP: {stats['vip']}
"""
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ---------- افزودن محصول (چند مرحله‌ای) ----------
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    state = context.user_data.get("admin_state")
    text = update.message.text if update.message.text else None

    # مرحله ۱: نام دسته‌بندی جدید
    if state == "waiting_category_name":
        data = load_products()
        cat_id = f"cat_{int(datetime.now().timestamp())}"
        data["categories"][cat_id] = {
            "name": text,
            "parent": None,
            "products": []
        }
        save_products(data)
        context.user_data.clear()
        await update.message.reply_text(f"✅ دسته‌بندی «{text}» ساخته شد.", reply_markup=admin_menu_keyboard())
        return

    # مرحله‌های افزودن محصول
    if state == "waiting_product_name":
        context.user_data["new_product"] = {"name": text}
        context.user_data["admin_state"] = "waiting_product_price"
        await update.message.reply_text("💰 قیمت محصول را به تومان وارد کنید (فقط عدد):")
        return

    if state == "waiting_product_price":
        try:
            price = int(text.replace(",", "").replace("،", "").strip())
            context.user_data["new_product"]["price"] = price
            context.user_data["admin_state"] = "waiting_product_description"
            await update.message.reply_text("📝 توضیحات محصول را بنویسید:")
        except:
            await update.message.reply_text("❌ قیمت نامعتبر است. فقط عدد وارد کنید:")
        return

    if state == "waiting_product_description":
        context.user_data["new_product"]["description"] = text
        context.user_data["admin_state"] = "waiting_product_photo"
        await update.message.reply_text("🖼 عکس محصول را ارسال کنید:\n(یا بنویسید «بدون عکس»)")
        return

    if state == "waiting_product_photo":
        if text and "بدون عکس" in text:
            context.user_data["new_product"]["photo"] = None
            await save_new_product(update, context)
        else:
            await update.message.reply_text("لطفاً یک عکس ارسال کنید یا بنویسید «بدون عکس»")

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("admin_state") != "waiting_product_photo":
        return

    photo = update.message.photo[-1]
    context.user_data["new_product"]["photo"] = photo.file_id
    await save_new_product(update, context)

async def save_new_product(update, context):
    product_data = context.user_data.get("new_product")
    category_id = context.user_data.get("add_product_category")

    if not product_data or not category_id:
        await update.message.reply_text("خطا در ذخیره محصول.")
        context.user_data.clear()
        return

    data = load_products()
    product_id = f"p{int(datetime.now().timestamp())}"
    product_data["id"] = product_id

    data["categories"][category_id]["products"].append(product_data)
    save_products(data)

    context.user_data.clear()
    await update.message.reply_text(
        f"✅ محصول «{product_data['name']}» با موفقیت اضافه شد.",
        reply_markup=admin_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("category_"):
        await show_products(query, data.replace("category_", ""))

    elif data.startswith("product_"):
        parts = data.split("_")
        if len(parts) >= 3:
            await show_product_detail(query, parts[1], parts[2])

    elif data == "feedback":
        await query.edit_message_text("📝 نقد یا پیشنهاد خود را بنویسید.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "club":
        await query.edit_message_text("⭐ باشگاه مشتریان\nامتیاز شما: ۰", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "about":
        await query.edit_message_text("ℹ️ ربات فروشگاهی هوشمند", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "back_main":
        context.user_data.clear()
        await query.edit_message_text("منوی اصلی:", reply_markup=main_menu_keyboard())

    elif data.startswith("addcart_"):
        await query.answer("به سبد اضافه شد (به زودی کامل می‌شود)", show_alert=True)

    # ادمین
    elif data.startswith("admin_") or data.startswith("addprod_") or data == "admin_back":
        if not is_admin(user_id):
            await query.answer("دسترسی غیرمجاز", show_alert=True)
            return

        if data == "admin_stats":
            await show_stats(query)

        elif data == "admin_back":
            context.user_data.clear()
            await query.edit_message_text("🛠️ پنل مدیریت", reply_markup=admin_menu_keyboard())

        elif data == "admin_add_category":
            context.user_data["admin_state"] = "waiting_category_name"
            await query.edit_message_text("➕ نام دسته‌بندی جدید را بفرستید:\n(لغو: /cancel)")

        elif data == "admin_add_product":
            await query.edit_message_text(
                "🛒 ابتدا دسته‌بندی مورد نظر را انتخاب کنید:",
                reply_markup=choose_category_keyboard()
            )

        elif data.startswith("addprod_cat_"):
            cat_id = data.replace("addprod_cat_", "")
            context.user_data["add_product_category"] = cat_id
            context.user_data["admin_state"] = "waiting_product_name"
            await query.edit_message_text("📝 نام محصول را وارد کنید:")

        elif data == "admin_manage_products":
            await query.edit_message_text("📦 بخش حذف و ویرایش محصولات به زودی اضافه می‌شود.", 
                reply_markup=admin_menu_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("عملیات لغو شد.", reply_markup=admin_menu_keyboard())

# ============================================================
# سرور
# ============================================================
async def health(request):
    return web.Response(text="Bot is alive ✅")

async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.exception("Webhook error")
        return web.Response(status=500)

async def main():
    global application
    TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_admin_photo))

    await application.initialize()
    await application.start()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post("/webhook", telegram_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info("Bot started successfully")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
