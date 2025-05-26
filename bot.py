from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from threading import Thread
import socket
import os

TOKEN = "7901391418:AAGVw38YRgxBTj-jvU9Ya3QS_9Q466Og1O4"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"

# Простой HTTP-сервер для удовлетворения требований Render
def run_dummy_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', int(os.environ.get('PORT', 10000))))
        s.listen()
        while True:
            conn, addr = s.accept()
            conn.sendall(b"HTTP/1.1 200 OK\n\nBot is running")
            conn.close()

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

            # Сохраняем данные поста
            post_data = {
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

            # Отправляем контент админу в зависимости от типа
            if update.message.photo:
                admin_msg = await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=post_data["photo"],
                    caption=admin_text,
                    reply_markup=reply_markup
                )
            elif update.message.video:
                admin_msg = await context.bot.send_video(
                    chat_id=ADMIN_ID,
                    video=post_data["video"],
                    caption=admin_text,
                    reply_markup=reply_markup
                )
            elif update.message.document:
                admin_msg = await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=post_data["document"],
                    caption=admin_text,
                    reply_markup=reply_markup
                )
            else:
                admin_msg = await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_text,
                    reply_markup=reply_markup
                )

            pending_posts[admin_msg.message_id] = post_data

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

def main():
    # Запускаем простой HTTP-сервер в отдельном потоке
    Thread(target=run_dummy_server, daemon=True).start()
    
    # Создаем и запускаем Telegram бота
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        print(f"Ошибка в боте: {e}")

if __name__ == "__main__":
    main()