import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8440165794

DB_NAME = "aliasdvpn.db"

# Render automatically provides PORT
PORT = int(os.getenv("PORT", "10000"))


# =========================================================
# PRODUCT ADDING STEPS
# =========================================================

NAME, TYPE, DURATION, VOLUME, USERS, PRICE, STOCK = range(7)


# =========================================================
# RENDER WEB SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

        self.wfile.write(
            b"AliasdVPN Bot is running!"
        )

    def do_HEAD(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_web_server():
    try:
        server = HTTPServer(
            ("0.0.0.0", PORT),
            HealthHandler
        )

        print(f"🌐 Render web server started on port {PORT}")

        server.serve_forever()

    except Exception as e:
        print(f"❌ Web server error: {e}")


# =========================================================
# DATABASE
# =========================================================

def db():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_type TEXT NOT NULL,
            duration TEXT NOT NULL,
            volume TEXT NOT NULL,
            users TEXT NOT NULL,
            price TEXT NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO users
        (id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name
    ))

    conn.commit()
    conn.close()


# =========================================================
# KEYBOARDS
# =========================================================

def main_menu(user_id):

    buttons = [
        [
            InlineKeyboardButton(
                "🛒 خرید کانفیگ",
                callback_data="shop"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 سفارش‌های من",
                callback_data="orders"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 پشتیبانی",
                callback_data="support"
            )
        ],
    ]

    if user_id == ADMIN_ID:

        buttons.append([
            InlineKeyboardButton(
                "👑 پنل مدیریت",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def admin_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="add_product"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 محصولات",
                callback_data="products"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="stats"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 فروشگاه",
                callback_data="home"
            )
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    save_user(user)

    await update.message.reply_text(
        "👋 سلام!\n\n"
        "به فروشگاه AliasdVPN خوش آمدید.\n\n"
        "🛒 از منوی زیر گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_menu(user.id)
    )


# =========================================================
# CALLBACK BUTTONS
# =========================================================

async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    if query.data == "home":

        await query.edit_message_text(
            "🏠 فروشگاه AliasdVPN\n\n"
            "گزینه موردنظر را انتخاب کنید:",
            reply_markup=main_menu(user_id)
        )

    # -----------------------------------------------------
    # SHOP
    # -----------------------------------------------------

    elif query.data == "shop":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                name,
                config_type,
                duration,
                volume,
                users,
                price,
                stock
            FROM products
        """)

        products = cur.fetchall()

        conn.close()

        if not products:

            await query.edit_message_text(
                "🛒 فروشگاه\n\n"
                "فعلاً محصولی برای فروش ثبت نشده است.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 برگشت",
                            callback_data="home"
                        )
                    ]
                ])
            )

            return

        text = "🛒 محصولات موجود:\n\n"

        buttons = []

        for product in products:

            (
                pid,
                name,
                ctype,
                duration,
                volume,
                users,
                price,
                stock
            ) = product

            text += (
                f"📦 {name}\n"
                f"🔹 نوع: {ctype}\n"
                f"⏳ مدت: {duration}\n"
                f"📊 حجم: {volume}\n"
                f"👤 کاربر: {users}\n"
                f"💰 قیمت: {price}\n"
                f"📦 موجودی: {stock}\n\n"
            )

            buttons.append([
                InlineKeyboardButton(
                    f"🛍 خرید {name}",
                    callback_data=f"buy_{pid}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    elif query.data == "orders":

        await query.edit_message_text(
            "📦 سفارش‌های من\n\n"
            "هنوز سفارشی ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    elif query.data == "support":

        await query.edit_message_text(
            "💬 پشتیبانی\n\n"
            "برای ارتباط با پشتیبانی، فعلاً "
            "از طریق مدیر فروشگاه اقدام کنید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ])
        )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    elif query.data == "admin":

        if user_id != ADMIN_ID:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

        await query.edit_message_text(
            "👑 پنل مدیریت AliasdVPN\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=admin_menu()
        )

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    elif query.data == "products":

        if user_id != ADMIN_ID:
            return

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                name,
                config_type,
                duration,
                volume,
                users,
                price,
                stock
            FROM products
        """)

        products = cur.fetchall()

        conn.close()

        if not products:

            text = "📦 هنوز هیچ محصولی ثبت نشده است."

        else:

            text = "📦 لیست محصولات:\n\n"

            for p in products:

                (
                    pid,
                    name,
                    ctype,
                    duration,
                    volume,
                    users,
                    price,
                    stock
                ) = p

                text += (
                    f"🆔 {pid}\n"
                    f"📦 {name}\n"
                    f"🔹 {ctype}\n"
                    f"⏳ {duration}\n"
                    f"📊 {volume}\n"
                    f"👤 {users}\n"
                    f"💰 {price}\n"
                    f"📦 موجودی: {stock}\n"
                    f"━━━━━━━━━━━━\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    elif query.data == "stats":

        if user_id != ADMIN_ID:
            return

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )

        users_count = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM products"
        )

        products_count = cur.fetchone()[0]

        cur.execute(
            "SELECT COALESCE(SUM(stock), 0) FROM products"
        )

        stock = cur.fetchone()[0]

        conn.close()

        await query.edit_message_text(
            "📊 آمار AliasdVPN\n\n"
            f"👥 کاربران: {users_count}\n"
            f"📦 محصولات: {products_count}\n"
            f"🛒 موجودی کل: {stock}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    elif query.data.startswith("buy_"):

        try:
            product_id = int(
                query.data.split("_")[1]
            )

        except (IndexError, ValueError):

            await query.answer(
                "❌ محصول نامعتبر است.",
                show_alert=True
            )

            return

        conn = db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                name,
                config_type,
                duration,
                volume,
                users,
                price,
                stock
            FROM products
            WHERE id = ?
        """, (product_id,))

        product = cur.fetchone()

        conn.close()

        if not product:

            await query.answer(
                "محصول پیدا نشد.",
                show_alert=True
            )

            return

        (
            name,
            ctype,
            duration,
            volume,
            users,
            price,
            stock
        ) = product

        await query.edit_message_text(
            f"🛒 {name}\n\n"
            f"🔹 نوع: {ctype}\n"
            f"⏳ مدت: {duration}\n"
            f"📊 حجم: {volume}\n"
            f"👤 تعداد کاربر: {users}\n"
            f"💰 قیمت: {price}\n"
            f"📦 موجودی: {stock}\n\n"
            "💳 سیستم پرداخت در مرحله بعد اضافه خواهد شد.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 محصولات",
                        callback_data="shop"
                    )
                ]
            ])
        )


# =========================================================
# ADD PRODUCT
# =========================================================

async def add_product_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.from_user.id != ADMIN_ID:

        return ConversationHandler.END

    await query.edit_message_text(
        "➕ افزودن محصول\n\n"
        "مرحله ۱ از ۷\n\n"
        "نام محصول را وارد کن:\n"
        "مثال: VLESS 100GB"
    )

    return NAME


async def product_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        "مرحله ۲ از ۷\n\n"
        "نوع کانفیگ را وارد کن:\n"
        "مثال: VLESS / VMess / Trojan / WireGuard"
    )

    return TYPE


async def product_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["type"] = update.message.text

    await update.message.reply_text(
        "مرحله ۳ از ۷\n\n"
        "مدت اعتبار را وارد کن:\n"
        "مثال: 30 روز"
    )

    return DURATION


async def product_duration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["duration"] = update.message.text

    await update.message.reply_text(
        "مرحله ۴ از ۷\n\n"
        "حجم را وارد کن:\n"
        "مثال: 100GB\n"
        "یا نامحدود"
    )

    return VOLUME


async def product_volume(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["volume"] = update.message.text

    await update.message.reply_text(
        "مرحله ۵ از ۷\n\n"
        "تعداد کاربر را وارد کن:\n"
        "مثال: 1"
    )

    return USERS


async def product_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["users"] = update.message.text

    await update.message.reply_text(
        "مرحله ۶ از ۷\n\n"
        "قیمت محصول را وارد کن:\n"
        "مثال: 150000 تومان"
    )

    return PRICE


async def product_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["price"] = update.message.text

    await update.message.reply_text(
        "مرحله ۷ از ۷\n\n"
        "تعداد موجودی اولیه را وارد کن:\n"
        "مثال: 10"
    )

    return STOCK


async def product_stock(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        stock = int(
            update.message.text
        )

    except ValueError:

        await update.message.reply_text(
            "❌ موجودی باید یک عدد باشد.\n"
            "مثلاً: 10"
        )

        return STOCK

    data = context.user_data

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products
        (
            name,
            config_type,
            duration,
            volume,
            users,
            price,
            stock
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["type"],
        data["duration"],
        data["volume"],
        data["users"],
        data["price"],
        stock
    ))

    conn.commit()
    conn.close()

    product_name_value = data["name"]
    product_type_value = data["type"]
    product_duration_value = data["duration"]
    product_volume_value = data["volume"]
    product_users_value = data["users"]
    product_price_value = data["price"]

    context.user_data.clear()

    await update.message.reply_text(
        "✅ محصول با موفقیت اضافه شد!\n\n"
        f"📦 نام: {product_name_value}\n"
        f"🔹 نوع: {product_type_value}\n"
        f"⏳ مدت: {product_duration_value}\n"
        f"📊 حجم: {product_volume_value}\n"
        f"👤 کاربر: {product_users_value}\n"
        f"💰 قیمت: {product_price_value}\n"
        f"📦 موجودی: {stock}",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


async def cancel_add(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ افزودن محصول لغو شد.",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        f"❌ TELEGRAM ERROR: {context.error}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    # Initialize database
    init_db()

    # Create Telegram application
    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # ADD PRODUCT CONVERSATION
    # -----------------------------------------------------

    add_product_conversation = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                add_product_start,
                pattern="^add_product$"
            )
        ],

        states={

            NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_name
                )
            ],

            TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_type
                )
            ],

            DURATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_duration
                )
            ],

            VOLUME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_volume
                )
            ],

            USERS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_users
                )
            ],

            PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_price
                )
            ],

            STOCK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    product_stock
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_add
            )
        ],

        per_message=False
    )

    # -----------------------------------------------------
    # TELEGRAM HANDLERS
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        add_product_conversation
    )

    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    app.add_error_handler(
        error_handler
    )

    # -----------------------------------------------------
    # START TELEGRAM BOT
    # -----------------------------------------------------

    print("🤖 AliasdVPN Bot is running...")

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# PROGRAM START
# =========================================================

if __name__ == "__main__":

    # Start Render HTTP server in background
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # Start Telegram bot
    main()