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
ORDERS_FILE = "orders.json"

# ============================================================
# ابزارهای کمکی
# ============================================================
def load_json(file, default=None):
    if default is None:
        default = {}
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================================
# مدیریت کاربران
# ============================================================
def get_or_create_user(user_id, username=None, full_name=None):
    users = load_json(USERS_FILE)
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "phone": None,
            "address": None,
            "level": 3,
            "cart": [],
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }
        save_json(USERS_FILE, users)
    else:
        users[uid]["last_seen"] = datetime.now().isoformat()
        if username:
            users[uid]["username"] = username
        if "cart" not in users[uid]:
            users[uid]["cart"] = []
        save_json(USERS_FILE, users)
    return users[uid]

def upgrade_user_level(user_id, new_level):
    users = load_json(USERS_FILE)
    uid = str(user_id)
    if uid not in users:
        return
    order = {3: 0, 2: 1, 1: 2, "vip": 3}
    current = users[uid].get("level", 3)
    if order.get(new_level, -1) > order.get(current, -1):
        users[uid]["level"] = new_level
        save_json(USERS_FILE, users)

def get_user_cart(user_id):
    users = load_json(USERS_FILE)
    return users.get(str(user_id), {}).get("cart", [])

def save_user_cart(user_id, cart):
    users = load_json(USERS_FILE)
    uid = str(user_id)
    if uid in users:
        users[uid]["cart"] = cart
        save_json(USERS_FILE, users)

def get_stats():
    users = load_json(USERS_FILE)
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
    data = load_json(PRODUCTS_FILE, {"categories": {}})
    if "categories" not in data:
        data = {"categories": {}}
        save_json(PRODUCTS_FILE, data)
    return data

def save_products(data):
    save_json(PRODUCTS_FILE, data)

def get_categories():
    return load_products().get("categories", {})

def get_root_categories():
    cats = get_categories()
    return {k: v for k, v in cats.items() if v.get("level") == 1}

def get_children(parent_id):
    cats = get_categories()
    return {k: v for k, v in cats.items() if v.get("parent") == parent_id}

def find_product(product_id):
    cats = get_categories()
    for cat_id, cat in cats.items():
        for p in cat.get("products", []):
            if p["id"] == product_id:
                return p, cat_id
    return None, None

# ============================================================
# مدیریت سفارش‌ها
# ============================================================
def save_order(order):
    orders = load_json(ORDERS_FILE, [])
    orders.append(order)
    save_json(ORDERS_FILE, orders)

def get_orders():
    return load_json(ORDERS_FILE, [])

# ============================================================
# کیبوردها
# ============================================================
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
        InlineKeyboardButton("🛒 سبد خرید", callback_data="show_cart"),
        InlineKeyboardButton("⭐ باشگاه مشتریان", callback_data="club")
    ])
    keyboard.append([
        InlineKeyboardButton("📝 نقد و پیشنهاد", callback_data="feedback"),
        InlineKeyboardButton("ℹ️ درباره ما", callback_data="about")
    ])
    return InlineKeyboardMarkup(keyboard)

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن دسته‌بندی سطح ۱", callback_data="admin_add_cat1")],
        [InlineKeyboardButton("📂 افزودن زیر‌دسته", callback_data="admin_add_sub")],
        [InlineKeyboardButton("🛒 افزودن محصول", callback_data="admin_add_product")],
        [InlineKeyboardButton("🗑 حذف محصول", callback_data="admin_delete_product")],
        [InlineKeyboardButton("📦 سفارش‌های جدید", callback_data="admin_orders")],
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
    upgrade_user_level(query.from_user.id, 2)
    cats = get_categories()
    category = cats.get(cat_id)
    if not category:
        await query.edit_message_text("دسته‌بندی یافت نشد.")
        return

    children = get_children(cat_id)
    products = category.get("products", [])
    text = f"📂 {category['name']}\n\n"
    keyboard = []

    for cid, cdata in children.items():
        keyboard.append([InlineKeyboardButton(f"📁 {cdata['name']}", callback_data=f"cat_{cid}")])

    for p in products:
        btn = f"{p['name']} | {p['price']:,} تومان"
        keyboard.append([InlineKeyboardButton(btn, callback_data=f"product_{cat_id}_{p['id']}")])

    if not children and not products:
        text += "هنوز موردی اضافه نشده."

    parent = category.get("parent")
    if parent:
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{parent}")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_product_detail(query, cat_id, product_id):
    product, _ = find_product(product_id)
    if not product:
        await query.edit_message_text("محصول یافت نشد.")
        return

    text = f"""
🛍 **{product['name']}**

💰 قیمت: {product['price']:,} تومان

📝 {product.get('description', '-')}
"""
    keyboard = [
        [InlineKeyboardButton("🛒 افزودن به سبد خرید", callback_data=f"addcart_{product_id}")],
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

async def show_cart(query):
    user_id = query.from_user.id
    cart = get_user_cart(user_id)

    if not cart:
        await query.edit_message_text(
            "🛒 سبد خرید شما خالی است.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")]])
        )
        return

    text = "🛒 **سبد خرید شما:**\n\n"
    total = 0
    keyboard = []

    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} - {item['price']:,} تومان\n"
        total += item["price"]
        keyboard.append([InlineKeyboardButton(f"❌ حذف {item['name']}", callback_data=f"removecart_{i}")])

    text += f"\n💰 جمع کل: {total:,} تومان"
    keyboard.append([InlineKeyboardButton("✅ نهایی کردن سفارش", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_main")])

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
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]), parse_mode="Markdown")

async def show_orders(query):
    orders = get_orders()
    if not orders:
        await query.edit_message_text("هنوز سفارشی ثبت نشده.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]))
        return

    text = "📦 **آخرین سفارش‌ها:**\n\n"
    for order in orders[-10:][::-1]:
        text += f"🆔 {order['id']}\n"
        text += f"👤 {order['name']} | {order['phone']}\n"
        text += f"💰 {order['total']:,} تومان\n"
        text += f"📅 {order['date'][:16]}\n"
        text += "────────────\n"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]))

# ---------- مدیریت state ادمین و کاربر ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = context.user_data.get("state")

    # ----- بخش ادمین -----
    if is_admin(user_id):
        admin_state = context.user_data.get("admin_state")

        if admin_state == "waiting_cat1_name":
            data = load_products()
            cat_id = f"c1_{int(datetime.now().timestamp())}"
            data["categories"][cat_id] = {"name": text, "level": 1, "parent": None, "products": []}
            save_products(data)
            context.user_data.clear()
            await update.message.reply_text(f"✅ دسته‌بندی «{text}» ساخته شد.", reply_markup=admin_menu_keyboard())
            return

        if admin_state == "waiting_sub_name":
            parent_id = context.user_data.get("parent_for_sub")
            parent = get_categories().get(parent_id)
            if not parent:
                await update.message.reply_text("خطا.")
                return
            new_level = parent["level"] + 1
            if new_level > 3:
                await update.message.reply_text("حداکثر ۳ سطح مجاز است.")
                return
            data = load_products()
            cat_id = f"c{new_level}_{int(datetime.now().timestamp())}"
            data["categories"][cat_id] = {"name": text, "level": new_level, "parent": parent_id, "products": []}
            save_products(data)
            context.user_data.clear()
            await update.message.reply_text(f"✅ زیر‌دسته سطح {new_level} ساخته شد.", reply_markup=admin_menu_keyboard())
            return

        if admin_state == "waiting_product_name":
            context.user_data["new_product"] = {"name": text}
            context.user_data["admin_state"] = "waiting_product_price"
            await update.message.reply_text("💰 قیمت (فقط عدد):")
            return

        if admin_state == "waiting_product_price":
            try:
                price = int(text.replace(",", "").replace("،", ""))
                context.user_data["new_product"]["price"] = price
                context.user_data["admin_state"] = "waiting_product_desc"
                await update.message.reply_text("📝 توضیحات:")
            except:
                await update.message.reply_text("فقط عدد وارد کنید.")
            return

        if admin_state == "waiting_product_desc":
            context.user_data["new_product"]["description"] = text
            context.user_data["admin_state"] = "waiting_product_photo"
            await update.message.reply_text("🖼 عکس را بفرستید یا بنویسید «بدون عکس»:")
            return

        if admin_state == "waiting_product_photo" and "بدون عکس" in text:
            context.user_data["new_product"]["photo"] = None
            await finish_add_product(update, context)
            return

    # ----- بخش ثبت سفارش کاربر -----
    if state == "checkout_name":
        context.user_data["order_name"] = text
        context.user_data["state"] = "checkout_phone"
        await update.message.reply_text("📱 شماره تماس خود را وارد کنید:")
        return

    if state == "checkout_phone":
        context.user_data["order_phone"] = text
        context.user_data["state"] = "checkout_address"
        await update.message.reply_text("🏠 آدرس کامل خود را وارد کنید:")
        return

    if state == "checkout_address":
        context.user_data["order_address"] = text
        await finalize_order(update, context)
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("خطا.")
        return
    data = load_products()
    product["id"] = f"p{int(datetime.now().timestamp())}"
    data["categories"][cat_id]["products"].append(product)
    save_products(data)
    context.user_data.clear()
    await update.message.reply_text(f"✅ محصول «{product['name']}» اضافه شد.", reply_markup=admin_menu_keyboard())

async def finalize_order(update, context):
    user_id = update.effective_user.id
    cart = get_user_cart(user_id)
    if not cart:
        await update.message.reply_text("سبد خرید خالی است.")
        return

    total = sum(i["price"] for i in cart)
    order = {
        "id": f"ORD-{int(datetime.now().timestamp())}",
        "user_id": user_id,
        "name": context.user_data.get("order_name"),
        "phone": context.user_data.get("order_phone"),
        "address": context.user_data.get("order_address"),
        "items": cart,
        "total": total,
        "date": datetime.now().isoformat(),
        "status": "جدید"
    }
    save_order(order)

    # ارتقای سطح
    upgrade_user_level(user_id, 1)  # بالقوه
    # در صورت پرداخت واقعی بعداً VIP می‌شود. فعلاً برای نمونه VIP می‌کنیم:
    upgrade_user_level(user_id, "vip")

    # پاک کردن سبد
    save_user_cart(user_id, [])
    context.user_data.clear()

    await update.message.reply_text(
        f"""
✅ سفارش شما با موفقیت ثبت شد!

🆔 شماره سفارش: {order['id']}
💰 مبلغ کل: {total:,} تومان

به زودی با شما تماس گرفته می‌شود.
""",
        reply_markup=main_menu_keyboard()
    )

    # اطلاع به ادمین
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🛒 سفارش جدید!\n\n{order['name']}\n{order['phone']}\n{total:,} تومان"
            )
        except:
            pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("cat_"):
        await show_category(query, data[4:])

    elif data.startswith("product_"):
        parts = data.split("_")
        if len(parts) >= 3:
            await show_product_detail(query, parts[1], parts[2])

    elif data.startswith("addcart_"):
        product_id = data.replace("addcart_", "")
        product, _ = find_product(product_id)
        if product:
            cart = get_user_cart(user_id)
            cart.append({"id": product["id"], "name": product["name"], "price": product["price"]})
            save_user_cart(user_id, cart)
            await query.answer("✅ به سبد خرید اضافه شد", show_alert=True)
        else:
            await query.answer("محصول یافت نشد", show_alert=True)

    elif data == "show_cart":
        await show_cart(query)

    elif data.startswith("removecart_"):
        idx = int(data.replace("removecart_", ""))
        cart = get_user_cart(user_id)
        if 0 <= idx < len(cart):
            cart.pop(idx)
            save_user_cart(user_id, cart)
        await show_cart(query)

    elif data == "checkout":
        cart = get_user_cart(user_id)
        if not cart:
            await query.answer("سبد خالی است", show_alert=True)
            return
        context.user_data["state"] = "checkout_name"
        await query.edit_message_text("لطفاً نام و نام خانوادگی خود را وارد کنید:")

    elif data == "feedback":
        await query.edit_message_text("📝 نقد یا پیشنهاد خود را بنویسید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "club":
        user = get_or_create_user(user_id)
        level_text = {3: "عادی", 2: "علاقه‌مند", 1: "بالقوه", "vip": "VIP"}.get(user.get("level"), "عادی")
        await query.edit_message_text(f"⭐ باشگاه مشتریان\n\nسطح شما: {level_text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "about":
        await query.edit_message_text("ℹ️ ربات فروشگاهی نمونه کار", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="back_main")]]))

    elif data == "back_main":
        context.user_data.clear()
        await query.edit_message_text("منوی اصلی:", reply_markup=main_menu_keyboard())

    # ادمین
    elif data.startswith("admin_") or data.startswith("subparent_") or data.startswith("prodcat_") or data.startswith("delprod_") or data == "admin_back":
        if not is_admin(user_id):
            await query.answer("غیرمجاز", show_alert=True)
            return

        if data == "admin_stats":
            await show_stats(query)
        elif data == "admin_orders":
            await show_orders(query)
        elif data == "admin_back":
            context.user_data.clear()
            await query.edit_message_text("🛠️ پنل مدیریت", reply_markup=admin_menu_keyboard())
        elif data == "admin_add_cat1":
            context.user_data["admin_state"] = "waiting_cat1_name"
            await query.edit_message_text("نام دسته‌بندی سطح ۱ را بفرستید:")
        elif data == "admin_add_sub":
            cats = get_categories()
            possible = {k: v for k, v in cats.items() if v.get("level", 1) < 3}
            if not possible:
                await query.edit_message_text("ابتدا دسته‌بندی سطح ۱ بسازید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]))
                return
            keyboard = [[InlineKeyboardButton(f"{v['name']} (سطح {v['level']})", callback_data=f"subparent_{k}")] for k, v in possible.items()]
            keyboard.append([InlineKeyboardButton("لغو", callback_data="admin_back")])
            await query.edit_message_text("دسته والد را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif data.startswith("subparent_"):
            context.user_data["parent_for_sub"] = data.replace("subparent_", "")
            context.user_data["admin_state"] = "waiting_sub_name"
            await query.edit_message_text("نام زیر‌دسته را بفرستید:")
        elif data == "admin_add_product":
            cats = get_categories()
            if not cats:
                await query.edit_message_text("ابتدا دسته بسازید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]))
                return
            keyboard = [[InlineKeyboardButton(f"{v['name']} (سطح {v['level']})", callback_data=f"prodcat_{k}")] for k, v in cats.items()]
            keyboard.append([InlineKeyboardButton("لغو", callback_data="admin_back")])
            await query.edit_message_text("دسته محصول را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif data.startswith("prodcat_"):
            context.user_data["product_category"] = data.replace("prodcat_", "")
            context.user_data["admin_state"] = "waiting_product_name"
            await query.edit_message_text("نام محصول را وارد کنید:")
        elif data == "admin_delete_product":
            cats = get_categories()
            keyboard = []
            for cid, cat in cats.items():
                for p in cat.get("products", []):
                    keyboard.append([InlineKeyboardButton(f"❌ {p['name']}", callback_data=f"delprod_{cid}_{p['id']}")])
            if not keyboard:
                await query.edit_message_text("محصولی برای حذف وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_back")]]))
                return
            keyboard.append([InlineKeyboardButton("لغو", callback_data="admin_back")])
            await query.edit_message_text("محصول مورد نظر برای حذف را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif data.startswith("delprod_"):
            parts = data.split("_")
            if len(parts) >= 3:
                cat_id, prod_id = parts[1], parts[2]
                data_p = load_products()
                products = data_p["categories"][cat_id]["products"]
                data_p["categories"][cat_id]["products"] = [p for p in products if p["id"] != prod_id]
                save_products(data_p)
                await query.edit_message_text("✅ محصول حذف شد.", reply_markup=admin_menu_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("لغو شد.", reply_markup=main_menu_keyboard())

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

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
