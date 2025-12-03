import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)

app = Flask(__name__)

filters_data = {}  # chat wise filters


# ---------------- ADMIN CHECK ----------------
def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------- START ----------------
def start(update, context):
    update.message.reply_text("🤖 Filter Bot Activated with Webhook!")


# ---------------- ADD FILTER ----------------
def add_filter(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Only admins can add filters.")

    if not context.args:
        return msg.reply_text("❌ Usage: reply sticker/photo/text → `/f keyword`")

    keyword = context.args[0].lower()

    if not msg.reply_to_message:
        return msg.reply_text("❌ Reply to message to set filter.")

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
        return msg.reply_text("❌ Unsupported message type.")

    if chat_id not in filters_data:
        filters_data[chat_id] = {}

    filters_data[chat_id][keyword] = file_id

    msg.reply_text(f"✅ Filter set for: `{keyword}`", parse_mode="Markdown")


# ---------------- REMOVE FILTER ----------------
def stop_filter(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Admin only!")

    if not context.args:
        return msg.reply_text("❌ Usage: `/fstop keyword`")

    keyword = context.args[0].lower()

    if chat_id in filters_data and keyword in filters_data[chat_id]:
        del filters_data[chat_id][keyword]
        msg.reply_text(f"🗑 Removed filter: `{keyword}`", parse_mode="Markdown")
    else:
        msg.reply_text("❌ Filter not found.")


# ---------------- LIST FILTERS ----------------
def list_filters(update, context):
    chat_id = update.message.chat_id

    if chat_id not in filters_data or not filters_data[chat_id]:
        return update.message.reply_text("📭 No filters available.")

    text = "📌 **Active Filters:**\n\n"
    for k in filters_data[chat_id]:
        text += f"• `{k}`\n"

    update.message.reply_text(text, parse_mode="Markdown")


# ---------------- REMOVE ALL FILTERS ----------------
def stop_all(update, context):
    msg = update.message
    chat_id = msg.chat_id
    user_id = msg.from_user.id

    if not is_admin(chat_id, user_id):
        return msg.reply_text("⚠️ Admin only!")

    filters_data[chat_id] = {}
    msg.reply_text("🚫 All filters cleared.")


# ---------------- AUTO FILTER RESPONSE ----------------
def auto_filter(update, context):
    msg = update.message
    if not msg or not msg.text:
        return

    chat_id = msg.chat_id
    text = msg.text.lower()

    if chat_id not in filters_data:
        return

    for keyword, file_id in filters_data[chat_id].items():
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

            # Text fallback
            bot.send_message(chat_id, file_id)
            return


# ---------------- FLASK WEBHOOK ----------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK", 200


@app.route("/")
def home():
    return "Filter Bot Running with Webhook!", 200


# ---------------- DISPATCHER ----------------
from telegram.ext import Dispatcher

dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("f", add_filter))
dispatcher.add_handler(CommandHandler("fstop", stop_filter))
dispatcher.add_handler(CommandHandler("flist", list_filters))
dispatcher.add_handler(CommandHandler("fstopall", stop_all))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, auto_filter))


# ---------------- MAIN ----------------
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=PORT)
