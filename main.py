import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام!\n\n"
        "به فروشگاه AliasdVPN خوش آمدید.\n\n"
        "🛒 فروشگاه به‌زودی فعال می‌شود."
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    print("🤖 AliasdVPN Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()