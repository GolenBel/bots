from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from flask import Flask, request, jsonify
import os
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "7901391418:AAGVw38YRgxBTj-jvU9Ya3QS_9Q466Og1O4"  # Замени на свой токен!
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"

# Инициализация Flask
app = Flask(__name__)

# Глобальное хранилище для постов на модерации
pending_posts = {}

# Инициализация бота
application = Application.builder().token(TOKEN).build()

### --- Обработчики команд --- ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=chat_id,
                message_id=message_id
            )
            
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
            logger.error(f"Ошибка при пересылке админу: {e}")
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
                
                post_text = f"\n\n{post_data['content']}\n\nАвтор: {author_name}"
                
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
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="<b>Твой контент опубликован!</b>",
                    parse_mode='HTML'
                )

            except Exception as e:
                logger.error(f"Ошибка публикации: {e}")
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

    if admin_msg_id in pending_posts:
        del pending_posts[admin_msg_id]

### --- Webhook часть --- ###
@app.route('/')
def home():
    return "Бот работает!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        return jsonify(success=True)
    return jsonify(success=False), 403

def set_webhook():
    # URL твоего Render-приложения (замени на свой)
    webhook_url = "https://bots-amfj.onrender.com/webhook"
    application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook установлен: {webhook_url}")

### --- Запуск --- ###
if __name__ == "__main__":
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Установка webhook при старте
    set_webhook()

    # Запуск Flask-сервера
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)