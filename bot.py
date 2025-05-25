from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from threading import Thread
import socket
import os
from datetime import datetime

# Конфигурация (рекомендуется вынести в переменные окружения)
TOKEN = os.getenv('TELEGRAM_TOKEN', "7901391418:AAGQvROcM7j1Oq1L3CtItn2ZwlDhxVL1wAI")
ADMIN_ID = int(os.getenv('ADMIN_ID', 495544662))
TARGET_CHAT_ID = os.getenv('TARGET_CHAT_ID', "-1002645719218")

class BotServer:
    @staticmethod
    def run():
        """HTTP-сервер для Render с чистым ответом"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', int(os.getenv('PORT', 10000))))
            s.listen()
            while True:
                conn, _ = s.accept()
                response = (
                    "HTTP/1.1 200 OK\n"
                    "Content-Type: text/plain\n\n"
                    f"Content Moderation Bot\n"
                    f"Status: Online\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                conn.sendall(response.encode('utf-8'))
                conn.close()

class ContentModerator:
    def __init__(self):
        self.pending_posts = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start с чистым сообщением"""
        welcome_msg = """
        <b>🚀 Бот-модератор контента</b>

        Присылайте мемы, новости и интересные находки!
        Я передам их на проверку модератору.
        """
        await update.message.reply_text(welcome_msg, parse_mode='HTML')

    async def handle_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящего контента"""
        if update.message.chat.type != "private":
            return

        user = update.message.from_user
        try:
            # Пересылаем контент модератору
            forwarded = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            
            # Создаем клавиатуру для модерации
            keyboard = [
                [InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{update.message.chat_id}_{update.message.message_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{update.message.chat_id}_{update.message.message_id}")]
            ]
            
            # Сохраняем данные поста
            self.pending_posts[forwarded.message_id] = {
                "original_chat_id": update.message.chat_id,
                "original_message_id": update.message.message_id,
                "content": update.message.text or update.message.caption or "",
                "user": user.to_dict(),
                "media": {
                    "photo": update.message.photo[-1].file_id if update.message.photo else None,
                    "video": update.message.video.file_id if update.message.video else None,
                    "document": update.message.document.file_id if update.message.document else None
                }
            }

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📨 Новый контент от @{user.username or user.first_name}:",
                reply_to_message_id=forwarded.message_id,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            print(f"Moderation error: {e}")
            await update.message.reply_text("⚠️ Ошибка при отправке на модерацию")

    async def handle_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка решения модератора"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('_')
        action = data[0]
        post_id = query.message.message_id

        if post_id not in self.pending_posts:
            return await query.edit_message_text("❌ Пост уже обработан")

        post = self.pending_posts[post_id]
        author = post['user']
        author_name = f"@{author['username']}" if author['username'] else author['first_name']

        if action == "approve":
            try:
                content = f"{post['content']}\n\n👤 Автор: {author_name}"
                
                if post['media']['photo']:
                    await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=post['media']['photo'],
                        caption=content,
                        parse_mode='HTML'
                    )
                elif post['media']['video']:
                    await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=post['media']['video'],
                        caption=content,
                        parse_mode='HTML'
                    )
                elif post['media']['document']:
                    await context.bot.send_document(
                        chat_id=TARGET_CHAT_ID,
                        document=post['media']['document'],
                        caption=content,
                        parse_mode='HTML'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=TARGET_CHAT_ID,
                        text=content,
                        parse_mode='HTML'
                    )

                await context.bot.send_message(
                    chat_id=post['original_chat_id'],
                    text="✅ Ваш контент был опубликован!",
                    parse_mode='HTML'
                )
                await query.edit_message_text("✅ Контент опубликован")
                
            except Exception as e:
                print(f"Publish error: {e}")
                await query.edit_message_text("❌ Ошибка публикации")

        elif action == "reject":
            await context.bot.send_message(
                chat_id=post['original_chat_id'],
                text="❌ Ваш контент не прошел модерацию",
                parse_mode='HTML'
            )
            await query.edit_message_text("❌ Контент отклонен")

        del self.pending_posts[post_id]

def main():
    # Запуск фонового сервера
    Thread(target=BotServer.run, daemon=True).start()
    
    # Инициализация модератора
    moderator = ContentModerator()
    
    # Настройка бота
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", moderator.start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, moderator.handle_content))
    app.add_handler(CallbackQueryHandler(moderator.handle_decision))
    
    # Запуск бота
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()