from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from threading import Thread
import socket
import os

TOKEN = "7901391418:AAGVw38YRgxBTj-jvU9Ya3QS_9Q466Og1O4"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"

# Простой HTTP-сервер для Render
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
    # Яркое стартовое сообщение без рекламы
    await update.message.reply_text(
        "Ну давай давай нападай!\n\n"
        "Кидай сюда свой контент - мемы, новости, крутые находки!\n"
        "Я отправлю их на проверку, а если всё ок - опубликую для всех!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Как это работает?", callback_data="help")]
        ])
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Просто присылай мне что-то интересное - я передам модератору.\n\n"
             "Если контент одобрят - он появится в нашем канале с твоим авторством!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Понял, начинаю!", callback_data="start_post")]
        ])
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        user = update.message.from_user
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{chat_id}_{message_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{chat_id}_{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            admin_text = (
                f"Новый контент от @{user.username or user.first_name}\n"
                f"ID: {user.id}\n\n"
            )
            
            if update.message.text:
                admin_text += f"Текст:\n{update.message.text}"
            elif update.message.caption:
                admin_text += f"Подпись:\n{update.message.caption}"

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
            await update.message.reply_text("Ой, что-то пошло не так... Попробуй еще раз!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    admin_msg_id = query.message.message_id

    if data == "help":
        await help_callback(update, context)
        return
    elif data == "start_post":
        await query.edit_message_text("Отлично! Жду твой контент...")
        return

    if data.startswith("approve"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            try:
                author = post_data["user"]
                author_name = f"@{author['username']}" if author["username"] else author["first_name"]
                
                # Яркое оформление поста
                post_text = (
                    f"{post_data['content']}\n\n"
                    f"Автор: {author_name}\n"
                )

                if post_data["photo"]:
                    sent_msg = await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=post_data["photo"],
                        caption=post_text
                    )
                elif post_data["video"]:
                    sent_msg = await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=post_data["video"],
                        caption=post_text
                    )
                elif post_data["document"]:
                    sent_msg = await context.bot.send_document(
                        chat_id=TARGET_CHAT_ID,
                        document=post_data["document"],
                        caption=post_text
                    )
                else:
                    sent_msg = await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=post_text
                    )

                await query.edit_message_text("✅ Опубликовано с крутым призывом!")
                
                # Яркое уведомление автору
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="Твой контент взлетел в канал! Так держать!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Посмотреть пост", url=f"https://t.me/c/{TARGET_CHAT_ID[4:]}/{sent_msg.message_id}")]
                    ])
                )

            except Exception as e:
                print(f"Ошибка при публикации: {e}")
                await query.edit_message_text("❌ Не удалось опубликовать")
    elif data.startswith("reject"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            await context.bot.send_message(
                chat_id=post_data["original_chat_id"],
                text="Этот контент не прошел модерацию. Попробуй что-то другое!"
            )
        await query.edit_message_text("❌ Отклонено")

    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def main():
    # Запускаем HTTP-сервер
    Thread(target=run_dummy_server, daemon=True).start()
    
    # Настраиваем бота
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