import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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

TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_ID = 8440165794

# اطلاعات کارت
CARD_NUMBER = "6219861452365603"
CARD_OWNER = "علی اسدنژاد"

# Render port
# Render مقدار PORT را خودش تنظیم می‌کند.
# اگر در محیط توسعه PORT وجود نداشت، 10000 استفاده می‌شود.
PORT = int(os.environ.get("PORT", "10000"))

DB_NAME = "aliasdvpn.db"


# =========================================================
# CONVERSATION STATES
# =========================================================

(
    NAME,
    TYPE,
    DURATION,
    VOLUME,
    USERS,
    PRICE,
    STOCK,
) = range(7)

CONFIG_PRODUCT = 100
CONFIG_VALUE = 101


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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting_payment',
            receipt_file_id TEXT,
            config_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            config TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            order_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_user(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO users (id, username, first_name)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.username,
        user.first_name
    ))

    conn.commit()
    conn.close()


# =========================================================
# WEB SERVER FOR RENDER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.send_header(
                "Cache-Control",
                "no-cache"
            )
            self.end_headers()

            self.wfile.write(
                b"AliasdVPN Bot is running."
            )

        except Exception as e:
            print(
                f"HTTP GET error: {repr(e)}",
                flush=True
            )

    def do_HEAD(self):
        try:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.end_headers()
        except Exception as e:
            print(
                f"HTTP HEAD error: {repr(e)}",
                flush=True
            )

    def log_message(self, format, *args):
        return


class RenderHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_web_server():
    host = "0.0.0.0"

    try:
        print(
            "🌐 Starting Render HTTP server...",
            flush=True
        )
        print(
            f"🌐 Host: {host}",
            flush=True
        )
        print(
            f"🌐 PORT: {PORT}",
            flush=True
        )

        server = RenderHTTPServer(
            (host, PORT),
            HealthHandler
        )

        print(
            f"✅ Render HTTP server is listening on "
            f"{host}:{PORT}",
            flush=True
        )

        server.serve_forever()

    except Exception as e:
        print(
            f"❌ WEB SERVER ERROR: {repr(e)}",
            flush=True
        )
        raise


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
                "🔐 افزودن کانفیگ",
                callback_data="add_config"
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
                "🧾 سفارش‌ها",
                callback_data="admin_orders"
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


def back_home_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )
        ]
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(user)

    await update.message.reply_text(
        "👋 سلام!\n\n"
        "به فروشگاه AliasdVPN خوش آمدید.\n\n"
        "🛒 از منوی زیر گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_menu(user.id)
    )


# =========================================================
# SHOP
# =========================================================

async def show_shop(query):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.config_type,
            p.duration,
            p.volume,
            p.users,
            p.price,
            COUNT(c.id)
        FROM products p
        LEFT JOIN configs c
            ON p.id = c.product_id
            AND c.status = 'available'
        GROUP BY p.id
        ORDER BY p.id DESC
    """)

    products = cur.fetchall()
    conn.close()

    if not products:
        await query.edit_message_text(
            "🛒 فروشگاه\n\n"
            "فعلاً محصولی برای فروش ثبت نشده است.",
            reply_markup=back_home_keyboard()
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

        if stock > 0:
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


# =========================================================
# BUY PRODUCT
# =========================================================

async def create_order(query, context):
    user_id = query.from_user.id

    try:
        product_id = int(query.data.split("_")[1])
    except Exception:
        await query.answer(
            "❌ محصول نامعتبر است.",
            show_alert=True
        )
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.price,
            COUNT(c.id)
        FROM products p
        LEFT JOIN configs c
            ON p.id = c.product_id
            AND c.status = 'available'
        WHERE p.id = ?
        GROUP BY p.id
    """, (product_id,))

    product = cur.fetchone()

    if not product:
        conn.close()
        await query.answer(
            "❌ محصول پیدا نشد.",
            show_alert=True
        )
        return

    pid, name, price, stock = product

    if stock <= 0:
        conn.close()
        await query.answer(
            "❌ این محصول موجود نیست.",
            show_alert=True
        )
        return

    cur.execute("""
        SELECT id
        FROM orders
        WHERE user_id = ?
        AND product_id = ?
        AND status IN ('waiting_payment', 'receipt_sent')
        ORDER BY id DESC
        LIMIT 1
    """, (user_id, product_id))

    existing = cur.fetchone()

    if existing:
        order_id = existing[0]
        conn.close()

        await query.edit_message_text(
            f"⚠️ شما قبلاً برای این محصول سفارش شماره #{order_id} دارید.\n\n"
            "ابتدا رسید همان سفارش را ارسال کنید یا منتظر بررسی آن بمانید.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📦 سفارش‌های من",
                        callback_data="orders"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 محصولات",
                        callback_data="shop"
                    )
                ]
            ])
        )
        return

    cur.execute("""
        INSERT INTO orders
        (user_id, username, product_id, product_name, price, status)
        VALUES (?, ?, ?, ?, ?, 'waiting_payment')
    """, (
        user_id,
        query.from_user.username or "",
        pid,
        name,
        price
    ))

    order_id = cur.lastrowid

    conn.commit()
    conn.close()

    await query.edit_message_text(
        f"🧾 سفارش شما ثبت شد.\n\n"
        f"🆔 شماره سفارش: #{order_id}\n"
        f"📦 محصول: {name}\n"
        f"💰 مبلغ: {price}\n\n"
        "💳 لطفاً مبلغ سفارش را به کارت زیر واریز کنید:\n\n"
        f"💳 شماره کارت:\n"
        f"`{CARD_NUMBER}`\n\n"
        f"👤 به نام: {CARD_OWNER}\n\n"
        "📸 بعد از پرداخت، عکس واضح رسید را همینجا ارسال کنید.\n\n"
        "⚠️ پس از بررسی رسید توسط ادمین، در صورت تأیید، کانفیگ برای شما ارسال خواهد شد.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "❌ لغو سفارش",
                    callback_data=f"cancel_order_{order_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📦 سفارش‌های من",
                    callback_data="orders"
                )
            ]
        ])
    )


# =========================================================
# RECEIPT
# =========================================================

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(user)

    if not update.message.photo:
        return

    photo = update.message.photo[-1]

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_name,
            price,
            status
        FROM orders
        WHERE user_id = ?
        AND status = 'waiting_payment'
        ORDER BY id DESC
        LIMIT 1
    """, (user.id,))

    order = cur.fetchone()

    if not order:
        conn.close()

        await update.message.reply_text(
            "❌ سفارش فعالی برای ارسال رسید پیدا نشد.\n\n"
            "ابتدا از فروشگاه یک محصول انتخاب کنید."
        )
        return

    order_id, product_name, price, status = order

    cur.execute("""
        UPDATE orders
        SET
            status = 'receipt_sent',
            receipt_file_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        photo.file_id,
        order_id
    ))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ رسید سفارش #{order_id} دریافت شد.\n\n"
        "⏳ رسید برای ادمین ارسال شد.\n"
        "لطفاً منتظر تأیید پرداخت بمانید."
    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    caption = (
        "🧾 رسید پرداخت جدید\n\n"
        f"🆔 سفارش: #{order_id}\n"
        f"👤 نام: {user.first_name}\n"
        f"🔢 آیدی: {user.id}\n"
        f"📱 یوزرنیم: {username}\n"
        f"📦 محصول: {product_name}\n"
        f"💰 مبلغ: {price}\n\n"
        "⬇️ نتیجه بررسی را انتخاب کنید:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید پرداخت",
                callback_data=f"approve_{order_id}"
            ),
            InlineKeyboardButton(
                "❌ رد پرداخت",
                callback_data=f"reject_{order_id}"
            )
        ]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=caption,
        reply_markup=keyboard
    )


# =========================================================
# USER ORDERS
# =========================================================

async def show_user_orders(query):
    user_id = query.from_user.id

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_name,
            price,
            status,
            created_at
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (user_id,))

    orders = cur.fetchall()
    conn.close()

    if not orders:
        await query.edit_message_text(
            "📦 سفارش‌های من\n\n"
            "هنوز سفارشی ثبت نشده است.",
            reply_markup=back_home_keyboard()
        )
        return

    status_text = {
        "waiting_payment": "💳 منتظر پرداخت",
        "receipt_sent": "⏳ در انتظار بررسی رسید",
        "approved": "✅ تأیید شده",
        "rejected": "❌ رد شده",
        "cancelled": "🚫 لغو شده",
    }

    text = "📦 سفارش‌های من\n\n"

    for order in orders:
        order_id, name, price, status, created_at = order

        text += (
            f"🧾 سفارش #{order_id}\n"
            f"📦 {name}\n"
            f"💰 {price}\n"
            f"📌 وضعیت: {status_text.get(status, status)}\n"
            f"🕐 {created_at}\n"
            f"━━━━━━━━━━━━\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 فروشگاه",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# CANCEL ORDER
# =========================================================

async def cancel_order(query):
    try:
        order_id = int(query.data.split("_")[2])
    except Exception:
        return

    user_id = query.from_user.id

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT status
        FROM orders
        WHERE id = ?
        AND user_id = ?
    """, (order_id, user_id))

    order = cur.fetchone()

    if not order:
        conn.close()

        await query.answer(
            "سفارش پیدا نشد.",
            show_alert=True
        )
        return

    status = order[0]

    if status != "waiting_payment":
        conn.close()

        await query.answer(
            "این سفارش دیگر قابل لغو نیست.",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE orders
        SET
            status = 'cancelled',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (order_id,))

    conn.commit()
    conn.close()

    await query.edit_message_text(
        f"🚫 سفارش #{order_id} لغو شد.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🛒 فروشگاه",
                    callback_data="shop"
                )
            ]
        ])
    )


# =========================================================
# ADMIN APPROVE
# =========================================================

async def approve_order(query, context):
    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    try:
        order_id = int(query.data.split("_")[1])
    except Exception:
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            user_id,
            product_id,
            product_name,
            price,
            status
        FROM orders
        WHERE id = ?
    """, (order_id,))

    order = cur.fetchone()

    if not order:
        conn.close()

        await query.answer(
            "❌ سفارش پیدا نشد.",
            show_alert=True
        )
        return

    user_id, product_id, product_name, price, status = order

    if status != "receipt_sent":
        conn.close()

        await query.answer(
            "⚠️ این سفارش قبلاً بررسی شده یا وضعیت آن مناسب نیست.",
            show_alert=True
        )
        return

    cur.execute("""
        SELECT id, config
        FROM configs
        WHERE product_id = ?
        AND status = 'available'
        ORDER BY id ASC
        LIMIT 1
    """, (product_id,))

    config = cur.fetchone()

    if not config:
        conn.close()

        await query.answer(
            "❌ برای این محصول کانفیگ آماده موجود نیست.",
            show_alert=True
        )

        await query.message.reply_text(
            f"⚠️ سفارش #{order_id} قابل تأیید نیست.\n\n"
            f"برای محصول «{product_name}» کانفیگ آماده موجود نیست.\n"
            "ابتدا یک کانفیگ به موجودی محصول اضافه کنید."
        )
        return

    config_id, config_value = config

    cur.execute("""
        UPDATE configs
        SET
            status = 'sold',
            order_id = ?
        WHERE id = ?
        AND status = 'available'
    """, (
        order_id,
        config_id
    ))

    cur.execute("""
        UPDATE orders
        SET
            status = 'approved',
            config_id = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        config_id,
        order_id
    ))

    cur.execute("""
        SELECT COUNT(*)
        FROM configs
        WHERE product_id = ?
        AND status = 'available'
    """, (product_id,))

    remaining_stock = cur.fetchone()[0]

    cur.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
    """, (
        remaining_stock,
        product_id
    ))

    conn.commit()
    conn.close()

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ پرداخت سفارش #{order_id} تأیید شد.\n\n"
                f"📦 محصول: {product_name}\n\n"
                "🔐 کانفیگ شما:\n\n"
                f"`{config_value}`\n\n"
                "🙏 از خرید شما متشکریم.\n"
                "در صورت نیاز به پشتیبانی با ما در ارتباط باشید."
            ),
            parse_mode="Markdown"
        )

        customer_sent = True

    except Exception as e:
        print(
            f"Customer delivery error: {repr(e)}",
            flush=True
        )
        customer_sent = False

    await query.answer("✅ سفارش تأیید شد.")

    try:
        await query.edit_message_caption(
            caption=(
                f"✅ پرداخت تأیید شد\n\n"
                f"🧾 سفارش: #{order_id}\n"
                f"📦 محصول: {product_name}\n"
                f"💰 مبلغ: {price}\n"
                f"🔐 کانفیگ تحویل شد: {'بله' if customer_sent else 'خیر'}"
            )
        )
    except Exception as e:
        print(
            f"Admin caption update error: {repr(e)}",
            flush=True
        )


# =========================================================
# ADMIN REJECT
# =========================================================

async def reject_order(query, context):
    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    try:
        order_id = int(query.data.split("_")[1])
    except Exception:
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            user_id,
            product_name,
            price,
            status
        FROM orders
        WHERE id = ?
    """, (order_id,))

    order = cur.fetchone()

    if not order:
        conn.close()

        await query.answer(
            "❌ سفارش پیدا نشد.",
            show_alert=True
        )
        return

    user_id, product_name, price, status = order

    if status != "receipt_sent":
        conn.close()

        await query.answer(
            "⚠️ این سفارش قبلاً بررسی شده است.",
            show_alert=True
        )
        return

    cur.execute("""
        UPDATE orders
        SET
            status = 'rejected',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (order_id,))

    conn.commit()
    conn.close()

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ سفارش #{order_id} تأیید نشد.\n\n"
                f"📦 محصول: {product_name}\n"
                f"💰 مبلغ: {price}\n\n"
                "متأسفانه سفارش توسط ادمین مربوطه تأیید نشد.\n"
                "در صورت وجود مشکل، با پشتیبانی تماس بگیرید."
            )
        )

    except Exception as e:
        print(
            f"Customer rejection message error: {repr(e)}",
            flush=True
        )

    await query.answer("❌ سفارش رد شد.")

    try:
        await query.edit_message_caption(
            caption=(
                f"❌ پرداخت رد شد\n\n"
                f"🧾 سفارش: #{order_id}\n"
                f"📦 محصول: {product_name}\n"
                f"💰 مبلغ: {price}"
            )
        )
    except Exception as e:
        print(
            f"Admin rejection caption update error: {repr(e)}",
            flush=True
        )


# =========================================================
# ADMIN ORDERS
# =========================================================

async def show_admin_orders(query):
    if query.from_user.id != ADMIN_ID:
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            user_id,
            product_name,
            price,
            status,
            created_at
        FROM orders
        ORDER BY id DESC
        LIMIT 30
    """)

    orders = cur.fetchall()
    conn.close()

    if not orders:
        text = "🧾 هنوز هیچ سفارشی ثبت نشده است."

    else:
        status_text = {
            "waiting_payment": "💳 منتظر پرداخت",
            "receipt_sent": "⏳ منتظر بررسی",
            "approved": "✅ تأیید شده",
            "rejected": "❌ رد شده",
            "cancelled": "🚫 لغو شده",
        }

        text = "🧾 آخرین سفارش‌ها:\n\n"

        for order in orders:
            (
                order_id,
                user_id,
                product_name,
                price,
                status,
                created_at
            ) = order

            text += (
                f"🆔 #{order_id}\n"
                f"👤 {user_id}\n"
                f"📦 {product_name}\n"
                f"💰 {price}\n"
                f"📌 {status_text.get(status, status)}\n"
                f"🕐 {created_at}\n"
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


# =========================================================
# ADD PRODUCT
# =========================================================

async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text

    await update.message.reply_text(
        "مرحله ۲ از ۷\n\n"
        "نوع کانفیگ را وارد کن:\n"
        "مثال: VLESS / VMess / Trojan / WireGuard"
    )

    return TYPE


async def product_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["type"] = update.message.text

    await update.message.reply_text(
        "مرحله ۳ از ۷\n\n"
        "مدت اعتبار را وارد کن:\n"
        "مثال: 30 روز"
    )

    return DURATION


async def product_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["duration"] = update.message.text

    await update.message.reply_text(
        "مرحله ۴ از ۷\n\n"
        "حجم را وارد کن:\n"
        "مثال: 100GB یا نامحدود"
    )

    return VOLUME


async def product_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["volume"] = update.message.text

    await update.message.reply_text(
        "مرحله ۵ از ۷\n\n"
        "تعداد کاربر را وارد کن:\n"
        "مثال: 1"
    )

    return USERS


async def product_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["users"] = update.message.text

    await update.message.reply_text(
        "مرحله ۶ از ۷\n\n"
        "قیمت محصول را وارد کن:\n"
        "مثال: 150000 تومان"
    )

    return PRICE


async def product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["price"] = update.message.text

    await update.message.reply_text(
        "مرحله ۷ از ۷\n\n"
        "تعداد موجودی اولیه را وارد کن.\n\n"
        "⚠️ توجه: موجودی واقعی از تعداد کانفیگ‌های آزاد محاسبه می‌شود.\n"
        "مثلاً اگر 10 کانفیگ اضافه کنید، موجودی 10 نمایش داده می‌شود.\n\n"
        "مثال: 10"
    )

    return STOCK


async def product_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        int(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ موجودی باید یک عدد باشد.\n"
            "مثلاً: 10"
        )
        return STOCK

    stock = int(update.message.text)

    if stock < 0:
        await update.message.reply_text(
            "❌ موجودی نمی‌تواند منفی باشد."
        )
        return STOCK

    data = context.user_data

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products
        (name, config_type, duration, volume, users, price, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["type"],
        data["duration"],
        data["volume"],
        data["users"],
        data["price"],
        0
    ))

    product_id = cur.lastrowid

    conn.commit()
    conn.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ محصول با موفقیت اضافه شد!\n\n"
        f"🆔 شناسه محصول: {product_id}\n"
        f"📦 نام: {data['name']}\n"
        f"🔹 نوع: {data['type']}\n"
        f"⏳ مدت: {data['duration']}\n"
        f"📊 حجم: {data['volume']}\n"
        f"👤 کاربر: {data['users']}\n"
        f"💰 قیمت: {data['price']}\n\n"
        "⚠️ برای فروش، باید کانفیگ‌های واقعی این محصول را از بخش "
        "«🔐 افزودن کانفیگ» اضافه کنید.",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


# =========================================================
# ADD CONFIG
# =========================================================

async def add_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return ConversationHandler.END

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name
        FROM products
        ORDER BY id DESC
    """)

    products = cur.fetchall()
    conn.close()

    if not products:
        await query.edit_message_text(
            "❌ ابتدا حداقل یک محصول ایجاد کنید.",
            reply_markup=admin_menu()
        )
        return ConversationHandler.END

    buttons = []

    for pid, name in products:
        buttons.append([
            InlineKeyboardButton(
                f"📦 {name}",
                callback_data=f"config_product_{pid}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "❌ لغو",
            callback_data="admin"
        )
    ])

    await query.edit_message_text(
        "🔐 افزودن کانفیگ\n\n"
        "کانفیگ را برای کدام محصول می‌خواهید اضافه کنید؟",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return CONFIG_PRODUCT


async def select_config_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return ConversationHandler.END

    try:
        product_id = int(query.data.split("_")[2])
    except Exception:
        return ConversationHandler.END

    context.user_data["config_product_id"] = product_id

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT name FROM products WHERE id = ?",
        (product_id,)
    )

    product = cur.fetchone()
    conn.close()

    if not product:
        await query.edit_message_text(
            "❌ محصول پیدا نشد.",
            reply_markup=admin_menu()
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"🔐 افزودن کانفیگ برای:\n"
        f"📦 {product[0]}\n\n"
        "حالا کانفیگ واقعی را ارسال کنید.\n\n"
        "مثلاً لینک VLESS، VMess، Trojan یا متن کانفیگ.\n\n"
        "⚠️ هر بار فقط یک کانفیگ ارسال کنید."
    )

    return CONFIG_VALUE


async def save_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config_value = update.message.text.strip()

    if not config_value:
        await update.message.reply_text(
            "❌ کانفیگ خالی است. دوباره ارسال کنید."
        )
        return CONFIG_VALUE

    product_id = context.user_data.get("config_product_id")

    if not product_id:
        await update.message.reply_text(
            "❌ محصول انتخاب نشده است.",
            reply_markup=admin_menu()
        )
        return ConversationHandler.END

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT name FROM products WHERE id = ?",
        (product_id,)
    )

    product = cur.fetchone()

    if not product:
        conn.close()

        await update.message.reply_text(
            "❌ محصول پیدا نشد.",
            reply_markup=admin_menu()
        )
        return ConversationHandler.END

    cur.execute("""
        INSERT INTO configs
        (product_id, config, status)
        VALUES (?, ?, 'available')
    """, (
        product_id,
        config_value
    ))

    cur.execute("""
        SELECT COUNT(*)
        FROM configs
        WHERE product_id = ?
        AND status = 'available'
    """, (product_id,))

    stock = cur.fetchone()[0]

    cur.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
    """, (
        stock,
        product_id
    ))

    conn.commit()
    conn.close()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ کانفیگ با موفقیت به موجودی اضافه شد.\n\n"
        f"📦 محصول: {product[0]}\n"
        f"📦 موجودی فعلی: {stock}",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


async def cancel_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ افزودن کانفیگ لغو شد.",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


# =========================================================
# PRODUCTS ADMIN
# =========================================================

async def show_products_admin(query):
    if query.from_user.id != ADMIN_ID:
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.config_type,
            p.duration,
            p.volume,
            p.users,
            p.price,
            COUNT(c.id)
        FROM products p
        LEFT JOIN configs c
            ON p.id = c.product_id
            AND c.status = 'available'
        GROUP BY p.id
        ORDER BY p.id DESC
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
                f"🔐 کانفیگ آماده: {stock}\n"
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


# =========================================================
# STATS
# =========================================================

async def show_stats(query):
    if query.from_user.id != ADMIN_ID:
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM configs
        WHERE status = 'available'
    """)
    available_configs = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM configs
        WHERE status = 'sold'
    """)
    sold_configs = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'receipt_sent'
    """)
    pending_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'approved'
    """)
    approved_orders = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status = 'rejected'
    """)
    rejected_orders = cur.fetchone()[0]

    conn.close()

    await query.edit_message_text(
        "📊 آمار AliasdVPN\n\n"
        f"👥 کاربران: {users}\n"
        f"📦 محصولات: {products}\n"
        f"🔐 کانفیگ آماده: {available_configs}\n"
        f"📤 کانفیگ فروخته‌شده: {sold_configs}\n\n"
        f"⏳ سفارش‌های منتظر بررسی: {pending_orders}\n"
        f"✅ سفارش‌های تأییدشده: {approved_orders}\n"
        f"❌ سفارش‌های ردشده: {rejected_orders}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 پنل مدیریت",
                    callback_data="admin"
                )
            ]
        ])
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "home":
        await query.edit_message_text(
            "🏠 فروشگاه AliasdVPN\n\n"
            "گزینه موردنظر را انتخاب کنید:",
            reply_markup=main_menu(user_id)
        )

    elif data == "shop":
        await show_shop(query)

    elif data == "orders":
        await show_user_orders(query)

    elif data == "support":
        await query.edit_message_text(
            "💬 پشتیبانی\n\n"
            "برای ارتباط با پشتیبانی، با مدیر فروشگاه تماس بگیرید.",
            reply_markup=back_home_keyboard()
        )

    elif data == "admin":
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

    elif data == "products":
        await show_products_admin(query)

    elif data == "admin_orders":
        await show_admin_orders(query)

    elif data == "stats":
        await show_stats(query)

    elif data.startswith("buy_"):
        await create_order(query, context)

    elif data.startswith("cancel_order_"):
        await cancel_order(query)

    elif data.startswith("approve_"):
        await approve_order(query, context)

    elif data.startswith("reject_"):
        await reject_order(query, context)


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):
    print(
        f"ERROR: {repr(context.error)}",
        flush=True
    )


# =========================================================
# CANCEL ADD PRODUCT
# =========================================================

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ افزودن محصول لغو شد.",
        reply_markup=admin_menu()
    )

    return ConversationHandler.END


# =========================================================
# MAIN
# =========================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    print(
        f"🔌 Render PORT environment variable: {PORT}",
        flush=True
    )

    init_db()

    # =====================================================
    # RENDER WEB SERVER
    # =====================================================

    web_thread = threading.Thread(
        target=start_web_server,
        name="render-web-server",
        daemon=True
    )

    web_thread.start()

    print(
        f"🌐 Render HTTP server thread started on port {PORT}",
        flush=True
    )

    # =====================================================
    # TELEGRAM APPLICATION
    # =====================================================

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # =====================================================
    # ADD PRODUCT CONVERSATION
    # =====================================================

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
    )

    # =====================================================
    # ADD CONFIG CONVERSATION
    # =====================================================

    add_config_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                add_config_start,
                pattern="^add_config$"
            )
        ],

        states={
            CONFIG_PRODUCT: [
                CallbackQueryHandler(
                    select_config_product,
                    pattern=r"^config_product_\d+$"
                )
            ],

            CONFIG_VALUE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_config
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel_config
            )
        ],
    )

    # =====================================================
    # HANDLERS
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # ConversationHandlerها قبل از Callback عمومی
    app.add_handler(
        add_product_conversation
    )

    app.add_handler(
        add_config_conversation
    )

    # دریافت رسید عکس
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_receipt
        )
    )

    # Callbackهای عمومی
    app.add_handler(
        CallbackQueryHandler(
            buttons
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "🤖 AliasdVPN Bot is running...",
        flush=True
    )

    print(
        f"🌐 Render PORT: {PORT}",
        flush=True
    )

    # =====================================================
    # TELEGRAM POLLING
    # =====================================================

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
