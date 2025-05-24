from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"  # Замените на реальный ID группы/канала

pending_posts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_text = (
        "Присылайте мемы/новости/обои, я отправлю их на модерацию!\n\n"
        "Есть что показать? Кидай сюда 👇"
    )
    await update.message.reply_text(start_text)

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
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=chat_id,
                message_id=message_id
            )
            
            # Отправляем кнопки модерации
            admin_msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"Модерация поста от @{user.username or user.first_name}:",
                reply_markup=reply_markup
            )

            pending_posts[admin_msg.message_id] = {
                "original_chat_id": chat_id,
                "original_message_id": message_id,
                "original_content": update.message.text or update.message.caption or "",
                "user": user
            }
        except Exception as e:
            print(f"Ошибка: {e}")
            await update.message.reply_text("😕 Что-то пошло не так при отправке на модерацию...")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    admin_msg_id = query.message.message_id

    if data.startswith("approve"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            user = post_data["user"]
            try:
                # Форматируем сообщение как в вашем примере

                    f"Автор: @{user.username or user.first_name}"
    

                # Если это медиа-файл (фото/видео/документ)
                if update.message.photo:
                    await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=update.message.photo[-1].file_id,
                        caption=publication_text
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=update.message.video.file_id,
                        caption=publication_text
                    )
                else:
                    # Если это просто текст
                    await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=publication_text
                    )

                await query.edit_message_text("✅ Пост опубликован в нужном формате!")
                
                # Уведомляем автора
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="🎉 Твой пост был опубликован! Спасибо за контент!"
                )

            except Exception as e:
                print(f"Ошибка публикации: {e}")
                await query.edit_message_text("❌ Не удалось опубликовать пост.")
    elif data.startswith("reject"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            await context.bot.send_message(
                chat_id=post_data["original_chat_id"],
                text="😕 К сожалению, твой пост не прошел модерацию."
            )
        await query.edit_message_text("❌ Пост отклонен.")

    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()