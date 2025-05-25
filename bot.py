from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from threading import Thread
import socket
import os

TOKEN = "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"

# HTTP-сервер для Render
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
    # Центрированное сообщение без рекламы
    start_message = """
    <b>Ну давай давай нападай!</b>
    
    Присылай мемы, новости, крутые находки!
    Я отправлю их на модерацию.
    """
    await update.message.reply_text(start_message, parse_mode='HTML')

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
            # Пересылаем оригинальное сообщение админу
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=chat_id,
                message_id=message_id
            )
            
            # Отправляем кнопки модерации
            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"Модерация контента от @{user.username or user.first_name}:",
                reply_to_message_id=forwarded_msg.message_id,
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
                "document": update.message.document.file_id if update.message.document else None,
                "forwarded_msg_id": forwarded_msg.message_id
            }

        except Exception as e:
            print(f"Ошибка при пересылке админу: {e}")
            await update.message.reply_text("Ошибка при отправке на модерацию")

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
                
                # Форматирование поста
                post_text = f"""
                
                {post_data['content']}
                
                Автор: {author_name}
                """
                
                # Отправка контента
                if post_data["photo"]:
                    sent_msg = await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=post_data["photo"],
                        caption=post_text,
                        parse_mode='HTML'
                    )
                elif post_data["video"]:
                    sent_msg = await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=post_data["video"],
                        caption=post_text,
                        parse_mode='HTML'
                    )
                elif post_data["document"]:
                    sent_msg = await context.bot.send_document(
                        chat_id=TARGET_CHAT_ID,
                        document=post_data["document"],
                        caption=post_text,
                        parse_mode='HTML'
                    )
                else:
                    sent_msg = await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=post_text,
                        parse_mode='HTML'
                    )

                await query.edit_message_text("✅ Пост опубликован!")
                
                # Уведомление автору
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="<b>Твой контент опубликован!</b>",
                    parse_mode='HTML'
                )

            except Exception as e:
                print(f"Ошибка публикации: {e}")
                await query.edit_message_text("❌ Ошибка при публикации")
                
    elif data.startswith("reject"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            await context.bot.send_message(
                chat_id=post_data["original_chat_id"],
                text="<b>Твой контент не прошел модерацию</b>",
                parse_mode='HTML'
            )
        await query.edit_message_text("❌ Пост отклонен")

    # Удаляем из временного хранилища
    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def main():
    # Запуск HTTP-сервера
    Thread(target=run_dummy_server, daemon=True).start()
    
    # Настройка бота
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск
    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        print(f"Ошибка бота: {e}")

if __name__ == "__main__":
    main()