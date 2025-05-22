from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI"
ADMIN_ID = 495544662  # ID админа (можно узнать у @userinfobot)

# Хранение постов временно (в реальном проекте используйте БД)
pending_posts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Присылайте мемы/новости, я отправлю их на модерацию!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    # Кнопки для админа
    keyboard = [
        [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{chat_id}_{message_id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{chat_id}_{message_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Пересылаем сообщение админу
    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=chat_id,
        message_id=message_id
    )
    # Отправляем кнопки модерации
    admin_msg = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="Модерация:",
        reply_markup=reply_markup
    )

    # Сохраняем данные поста
    pending_posts[admin_msg.message_id] = {
        "original_chat_id": chat_id,
        "original_message_id": message_id
    }

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    admin_msg_id = query.message.message_id

    if data.startswith("approve"):
        post_data = pending_posts.get(admin_msg_id)
        if post_data:
            # Пересылаем в канал/группу
            await context.bot.forward_message(
                chat_id="@Graphyl",  # Замените на username канала
                from_chat_id=post_data["original_chat_id"],
                message_id=post_data["original_message_id"]
            )
            await query.edit_message_text("✅ Пост опубликован!")
        else:
            await query.edit_message_text("Ошибка: пост не найден.")
    elif data.startswith("reject"):
        await query.edit_message_text("❌ Пост отклонен.")

    # Удаляем из временного хранилища
    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()