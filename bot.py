from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from flask import Flask
from threading import Thread
import os

TOKEN = "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"  # Замените на реальный ID группы/канала

# Создаем Flask сервер для Render
server = Flask(__name__)

@server.route('/')
def home():
    return "Telegram Bot is running", 200

pending_posts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Присылайте мемы/новости, я отправлю их на модерацию!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        user = update.message.from_user
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{chat_id}_{message_id}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{chat_id}_{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            admin_text = f"Новый контент на модерацию от @{user.username or user.first_name} (ID: {user.id})"
            
            if update.message.text:
                admin_text += f"\n\nТекст: {update.message.text}"
            elif update.message.caption:
                admin_text += f"\n\nПодпись: {update.message.caption}"

            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=reply_markup
            )

            pending_posts[admin_msg.message_id] = {
                "original_chat_id": chat_id,
                "original_message_id": message_id,
                "content": update.message.text or update.message.caption or "",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                },
                "photo": update.message.photo[-1].file_id if update.message.photo else None,
                "video": update.message.video.file_id if update.message.video else None,
                "document": update.message.document.file_id if update.message.document else None
            }

        except Exception as e:
            print(f"Ошибка при пересылке админу: {e}")
            await update.message.reply_text("Произошла ошибка при отправке на модерацию.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    admin_msg_id = query.message.message_id

    if data.startswith("approve"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            try:
                author = post_data["user"]
                author_name = f"@{author['username']}" if author["username"] else author["first_name"]
                post_text = f"{post_data['content']}\n\nАвтор: {author_name}"

                if post_data["photo"]:
                    await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=post_data["photo"],
                        caption=post_text
                    )
                elif post_data["video"]:
                    await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=post_data["video"],
                        caption=post_text
                    )
                elif post_data["document"]:
                    await context.bot.send_document(
                        chat_id=TARGET_CHAT_ID,
                        document=post_data["document"],
                        caption=post_text
                    )
                else:
                    await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=post_text
                    )

                await query.edit_message_text("✅ Пост опубликован!")
                
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="Ваш пост был одобрен и опубликован!"
                )

            except Exception as e:
                print(f"Ошибка при публикации: {e}")
                await query.edit_message_text("❌ Ошибка при публикации поста.")
    elif data.startswith("reject"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            await context.bot.send_message(
                chat_id=post_data["original_chat_id"],
                text="Ваш пост был отклонен модератором."
            )
        await query.edit_message_text("❌ Пост отклонен.")

    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def run_flask():
    server.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

def main():
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask).start()
    
    # Создаем и запускаем Telegram бота
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"Ошибка в боте: {e}")

if __name__ == "__main__":
    main()