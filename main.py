import os
from flask import Flask
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)

# Flask just to keep service alive (no webhook)
app = Flask(__name__)

@app.route("/")
def home():
    return "Filter Bot Running (Polling)!", 200

# In-memory filters
filters = {}


# ------------------- ADMIN CHECK -------------------
def is_admin(chat_id, user_id):
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ["administrator", "creator"]
    except:
        return False


# ------------------- COMMANDS -------------------
def start(update, context):
    update.message.reply_text("🤖 Filter Bot Activated!")


def add_filter(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Only admins can add filters.")

    if not context.args:
        return msg.reply_text("❌ Usage: Reply sticker/photo/text → `/f keyword`")

    keyword = context.args[0].lower()

    if not msg.reply_to_message:
        return msg.reply_text("❌ Reply to a message to set filter.")

    rep = msg.reply_to_message

    # Sticker
    if rep.sticker:
        file_id = rep.sticker.file_id

    # Photo
    elif rep.photo:
        file_id = rep.photo[-1].file_id

    # Text
    elif rep.text:
        file_id = rep.text

    else:
        return msg.reply_text("❌ Unsupported media type.")

    if chat_id not in filters:
        filters[chat_id] = {}

    filters[chat_id][keyword] = file_id

    msg.reply_text(f"✅ Filter added for: `{keyword}`", parse_mode="Markdown")


def stop_filter(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Only admins can remove filters.")

    if not context.args:
        return msg.reply_text("❌ Usage: `/fstop keyword`")

    keyword = context.args[0].lower()

    if chat_id in filters and keyword in filters[chat_id]:
        del filters[chat_id][keyword]
        msg.reply_text(f"🗑 Removed filter: `{keyword}`", parse_mode="Markdown")
    else:
        msg.reply_text("❌ Filter not found.")


def list_filters(update, context):
    chat_id = update.message.chat_id

    if chat_id not in filters or not filters[chat_id]:
        return update.message.reply_text("📭 No filters set.")

    text = "📌 **Active Filters:**\n\n"
    for k in filters[chat_id]:
        text += f"• `{k}`\n"

    update.message.reply_text(text, parse_mode="Markdown")


def stop_all(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Only admins can clear all filters.")

    filters[chat_id] = {}
    msg.reply_text("🚫 All filters removed.")


# ------------------- AUTO FILTER -------------------
def auto_filter(update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat_id
    text = msg.text.lower()

    if chat_id not in filters:
        return

    for keyword, file_id in filters[chat_id].items():
        if keyword in text:

            # Try sticker
            try:
                bot.send_sticker(chat_id, file_id)
                return
            except:
                pass

            # Try photo
            try:
                bot.send_photo(chat_id, file_id)
                return
            except:
                pass

            # Default text
            bot.send_message(chat_id, file_id)
            return


# ------------------- MAIN -------------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("f", add_filter))
    dp.add_handler(CommandHandler("fstop", stop_filter))
    dp.add_handler(CommandHandler("flist", list_filters))
    dp.add_handler(CommandHandler("fstopall", stop_all))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, auto_filter))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    # Flask ko background me run karo (Render needs this)
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()

    # Bot polling
    main()