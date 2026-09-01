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
    except:
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
            "level": 3,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "categories_viewed": []
        }
        save_users(users)
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        save_users(users)
    return users[uid]

def upgrade_user_level(user_id, new_level):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        return
    order = {3: 0, 2: 1, 1: 2, "vip": 3}
    if order.get(new_level, -1) > order.get(users[uid]["level"], -1):
        users[uid]["level"] = new_level
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
# مدیریت محصولات (۳ سطحی)
# ============================================================
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        default = {"categories": {}}
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

def get_root_categories():
    cats = get_categories()
    return {k: v for k, v in cats.items() if v.get("level") == 1}

def get_children(parent_id):
    cats = get_categories()
    return {k: v for k, v in cats.items() if v.get("parent") == parent_id}

# ============================================================
# کیبوردها
# ============================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_menu_keyboard():
    roots = get_root_categories()
    keyboard = []
    items = list(roots.items())
    for i in range(0, len(items), 2):
        row = []
        cid, cdata = items[i]
        row.append(InlineKeyboardButton(cdata["name"], callback_data=f"cat_{cid}"))
        if i + 1 < len(items):
            cid2, cdata2 = items[i + 1]
            row.append(InlineKeyboardButton(cdata2["name"], callback_data=f"cat_{cid2}"))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback"),
        InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")
    ])
    keyboard.append([InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن دسته‌بندی سطح ۱", callback_data="admin_add_cat1")],
        [InlineKeyboardButton("📂 افزودن زیر‌دسته (سطح ۲ یا ۳)", callback_data="admin_add_sub")],
        [InlineKeyboardButton("🛒 افزودن محصول", callback_data="admin_add_product")],
        [InlineKeyboardButton("📊 آمار مشتریان", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ])

# ============================================================
# هندلرها
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.full_name)
    await update.message.reply_text(
        "سلام به ربات فروشگاهی خوش آمدید! 👋\n\nاز منوی زیر انتخاب کنید:",
        reply_markup=main_menu_keyboard()
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("دستور نامعتبر است.")
        return
    context.user_data.clear()
    await update.message.reply_text("🛠️ **پنل مدیریت**", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")

async def show_category(query, cat_id):
    user_id = query.from_user.id
    upgrade_user_level(user_id, 2)

    cats = get_categories()
    category = cats.get(cat_id)
    if not category:
        await query.edit_message_text("دسته‌بندی یافت نشد.")
        return

    children = get_children(cat_id)
    products = category.get("products", [])

    text = f"📂 {category['name']}\n\n"
    keyboard = []

    if children:
        for cid, cdata in children.items():
            keyboard.append([InlineKeyboardButton(f"📁 {cdata['name']}", callback_data=f"cat_{cid}")])

    if products:
        for p in products:
            btn = f"{p['name']} | {p['price']:,} تومان"
            keyboard.append([InlineKeyboardButton(btn, callback_data=f"product_{cat_id}_{p['id']}")])

    if not children and not products:
        text += "هنوز موردی اضافه نشده است."

    parent = category.get("parent")
    if parent:
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{parent}")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_product_detail(query, cat_id, product_id):
    cats = get_categories()
    category = cats.get(cat_id)
    if not category:
        await query.edit_message_text("یافت نشد.")
        return
    product = next((p for p in category.get("products", []) if p["id"] == product_id), None)
    if not product:
        await query.edit_message_text("محصول یافت نشد.")
        return

    text = f"""
🛍 **{product['name']}**

💰 قیمت: {product['price']:,} تومان

📝 {product.get('description', '')}
"""
    keyboard = [
        [InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"addcart_{product_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{cat_id}")]
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
🔹 عادی: {stats['level_3']}
🔸 علاقه‌مند: {stats['level_2']}
🔶 بالقوه: {stats['level_1']}
⭐ VIP: {stats['vip']}
"""
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]),
        parse_mode="Markdown"
    )

# ---------- پیام‌های ادمین ----------
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    state = context.user_data.get("admin_state")
    text = update.message.text

    if state == "waiting_cat1_name":
        data = load_products()
        cat_id = f"c1_{int(datetime.now().timestamp())}"
        data["categories"][cat_id] = {
            "name": text,
            "level": 1,
            "parent": None,
            "products": []
        }
        save_products(data)
        context.user_data.clear()
        await update.message.reply_text(f"✅ دسته‌بندی سطح ۱ «{text}» ساخته شد.", reply_markup=admin_menu_keyboard())
        return

    if state == "waiting_sub_name":
        parent_id = context.user_data.get("parent_for_sub")
        parent = get_categories().get(parent_id)
        if not parent:
            await update.message.reply_text("خطا: دسته والد یافت نشد.")
            context.user_data.clear()
            return

        new_level = parent["level"] + 1
        if new_level > 3:
            await update.message.reply_text("❌ حداکثر ۳ سطح مجاز است.")
            context.user_data.clear()
            return

        data = load_products()
        cat_id = f"c{new_level}_{int(datetime.now().timestamp())}"
        data["categories"][cat_id] = {
            "name": text,
            "level": new_level,
            "parent": parent_id,
            "products": []
        }
        save_products(data)
        context.user_data.clear()
        await update.message.reply_text(f"✅ زیر‌دسته‌بندی سطح {new_level} «{text}» ساخته شد.", reply_markup=admin_menu_keyboard())
        return

    if state == "waiting_product_name":
        context.user_data["new_product"] = {"name": text}
        context.user_data["admin_state"] = "waiting_product_price"
        await update.message.reply_text("💰 قیمت را به تومان وارد کنید (فقط عدد):")
        return

    if state == "waiting_product_price":
        try:
            price = int(text.replace(",", "").replace("،", "").strip())
            context.user_data["new_product"]["price"] = price
            context.user_data["admin_state"] = "waiting_product_desc"
            await update.message.reply_text("📝 توضیحات محصول را بنویسید:")
        except:
            await update.message.reply_text("❌ فقط عدد وارد کنید:")
        return

    if state == "waiting_product_desc":
        context.user_data["new_product"]["description"] = text
        context.user_data["admin_state"] = "waiting_product_photo"
        await update.message.reply_text("🖼 عکس محصول را بفرستید یا بنویسید «بدون عکس»:")
        return

    if state == "waiting_product_photo" and text and "بدون عکس" in text:
        context.user_data["new_product"]["photo"] = None
        await finish_add_product(update, context)

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("admin_state") != "waiting_product_photo":
        return

    photo = update.message.photo[-1]
    context.user_data["new_product"]["photo"] = photo.file_id
    await finish_add_product(update, context)

async def finish_add_product(update, context):
    product = context.user_data.get("new_product")
    cat_id = context.user_data.get("product_category")

    if not product or not cat_id:
        await update.message.reply_text("خطا در ذخیره.")
        context.user_data.clear()
        return

    data = load_products()
    product["id"] = f"p{int(datetime.now().timestamp())}"
    data["categories"][cat_id]["products"].append(product)
    save_products(data)

    context.user_data.clear()
    await update.message.reply_text(f"✅ محصول «{product['name']}» اضافه شد.", reply_markup=admin_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("cat_"):
        await show_category(query, data.replace("cat_", ""))

    elif data.startswith("product_"):
        parts = data.split("_")
        if len(parts) >= 3:
            await show_product_detail(query, parts[1], parts[2])

    elif data == "feedback":
        await query.edit_message_text("📝 نقد یا پیشنهاد خود را بنویسید.", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "club":
        await query.edit_message_text("⭐ باشگاه مشتریان\nامتیاز: ۰", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "about":
        await query.edit_message_text("ℹ️ ربات فروشگاهی", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "back_main":
        context.user_data.clear()
        await query.edit_message_text("منوی اصلی:", reply_markup=main_menu_keyboard())

    elif data.startswith("addcart_"):
        await query.answer("به سبد اضافه شد", show_alert=True)

    # ==================== بخش ادمین ====================
    elif data.startswith("admin_") or data.startswith("subparent_") or data.startswith("prodcat_") or data == "admin_back":
        if not is_admin(user_id):
            await query.answer("غیرمجاز", show_alert=True)
            return

        if data == "admin_stats":
            await show_stats(query)

        elif data == "admin_back":
            context.user_data.clear()
            await query.edit_message_text("🛠️ پنل مدیریت", reply_markup=admin_menu_keyboard())

        elif data == "admin_add_cat1":
            context.user_data["admin_state"] = "waiting_cat1_name"
            await query.edit_message_text("➕ نام دسته‌بندی سطح ۱ را بفرستید:")

        elif data == "admin_add_sub":
            cats = get_categories()
            # فقط دسته‌هایی که سطح کمتر از ۳ دارند می‌توانند زیر‌دسته داشته باشند
            possible_parents = {k: v for k, v in cats.items() if v.get("level", 1) < 3}

            if not possible_parents:
                await query.edit_message_text(
                    "❌ هنوز هیچ دسته‌بندی سطح ۱ وجود ندارد.\n\nابتدا یک دسته‌بندی سطح ۱ بسازید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]])
                )
                return

            keyboard = []
            for cid, cdata in possible_parents.items():
                level = cdata.get("level", 1)
                prefix = "—" * (level - 1)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prefix} {cdata['name']} (سطح {level})",
                        callback_data=f"subparent_{cid}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="admin_back")])
            await query.edit_message_text(
                "📂 دسته‌بندی والد را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("subparent_"):
            parent_id = data.replace("subparent_", "")
            context.user_data["parent_for_sub"] = parent_id
            context.user_data["admin_state"] = "waiting_sub_name"
            await query.edit_message_text("📝 نام زیر‌دسته‌بندی را بفرستید:")

        elif data == "admin_add_product":
            cats = get_categories()
            if not cats:
                await query.edit_message_text(
                    "❌ هنوز هیچ دسته‌بندی وجود ندارد.\nابتدا دسته‌بندی بسازید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]])
                )
                return

            keyboard = []
            for cid, cdata in cats.items():
                level = cdata.get("level", 1)
                prefix = "—" * (level - 1)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prefix} {cdata['name']} (سطح {level})",
                        callback_data=f"prodcat_{cid}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="admin_back")])
            await query.edit_message_text(
                "🛒 دسته‌بندی محصول را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("prodcat_"):
            cat_id = data.replace("prodcat_", "")
            context.user_data["product_category"] = cat_id
            context.user_data["admin_state"] = "waiting_product_name"
            await query.edit_message_text("📝 نام محصول را وارد کنید:")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("لغو شد.", reply_markup=admin_menu_keyboard())

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
        logger.exception("error")
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
    logger.info("Bot started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
