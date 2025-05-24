from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"  # Замените на реальный ID группы/канала

pending_posts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Присылайте мемы/новости, я отправлю их на модерацию!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":  # Только из личных сообщений
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{chat_id}_{message_id}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{chat_id}_{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
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

            pending_posts[admin_msg.message_id] = {
                "original_chat_id": chat_id,
                "original_message_id": message_id,
                "original_content": update.message.text or update.message.caption or ""
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
                # Попробуем сначала переслать
                await context.bot.forward_message(
                    chat_id=TARGET_CHAT_ID,
                    from_chat_id=post_data["original_chat_id"],
                    message_id=post_data["original_message_id"]
                )
                await query.edit_message_text("✅ Пост опубликован!")
            except Exception as e:
                print(f"Ошибка при пересылке: {e}")
                # Если не получилось переслать, попробуем отправить копию
                try:
                    await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=post_data["original_content"]
                    )
                    await query.edit_message_text("✅ Пост опубликован (текстовая копия)!")
                except Exception as e2:
                    print(f"Ошибка при отправке копии: {e2}")
                    await query.edit_message_text("❌ Ошибка при публикации поста.")
    elif data.startswith("reject"):
        await query.edit_message_text("❌ Пост отклонен.")

    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # Исправленный фильтр:
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()