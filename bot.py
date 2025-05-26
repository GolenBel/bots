from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from threading import Thread
import socket
import os
import time
import asyncio
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7901391418:AAGVw38YRgxBTj-jvU9Ya3QS_9Q466Og1O4"
ADMIN_ID = 495544662
TARGET_CHAT_ID = "-1002645719218"

# Интервал для ping-сообщений (в секундах)
PING_INTERVAL = 300  # 5 минут

pending_posts = {}

class BotPinger:
    def __init__(self, app):
        self.app = app
        self.is_running = True
        
    async def start_pinging(self):
        while self.is_running:
            try:
                # Получаем информацию о боте для проверки работы
                bot_info = await self.app.bot.get_me()
                logger.info(f"Bot ping successful: @{bot_info.username} is alive")
                
                # Отправляем ping в лог-чат (можно заменить на реальный чат)
                await self.app.bot.send_message(
                    chat_id=ADMIN_ID,
                    text="🤖 Бот активен и работает!",
                    disable_notification=True
                )
            except Exception as e:
                logger.error(f"Ping failed: {e}")
            
            await asyncio.sleep(PING_INTERVAL)

    def stop_pinging(self):
        self.is_running = False

# Простой HTTP-сервер для Render с улучшенной обработкой
def run_dummy_server():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', int(os.environ.get('PORT', 10000))))
                s.listen()
                s.settimeout(5)  # Таймаут для периодической проверки is_running
                
                while True:
                    try:
                        conn, addr = s.accept()
                        conn.sendall(b"HTTP/1.1 200 OK\n\nBot is running")
                        conn.close()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f"Server error: {e}")
                        break
        except Exception as e:
            logger.error(f"Server crashed: {e}, restarting in 10 seconds...")
            time.sleep(10)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            logger.error(f"Ошибка при пересылке админу: {e}")
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
                
                post_text = (
                    "Ну давай давай нападай!\n\n"
                    f"{post_data['content']}\n\n"
                    f"Автор: {author_name}\n"
                    "#круто #контент"
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
                
                await context.bot.send_message(
                    chat_id=post_data["original_chat_id"],
                    text="Твой контент взлетел в канал! Так держать!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Посмотреть пост", url=f"https://t.me/c/{TARGET_CHAT_ID[4:]}/{sent_msg.message_id}")]
                    ])
                )

            except Exception as e:
                logger.error(f"Ошибка при публикации: {e}")
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

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")
    
    # Попытка отправить сообщение об ошибке админу
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ Произошла ошибка: {context.error}"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

def main():
    # Запускаем HTTP-сервер в отдельном потоке
    server_thread = Thread(target=run_dummy_server, daemon=True)
    server_thread.start()
    
    # Настраиваем бота с обработкой ошибок
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(on_error)
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Система ping для поддержания активности
    pinger = BotPinger(app)
    
    async def run_bot():
        # Запускаем ping-систему
        asyncio.create_task(pinger.start_pinging())
        
        # Запускаем бота с автоматическим переподключением
        while True:
            try:
                await app.initialize()
                await app.start()
                await app.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                
                logger.info("Bot started successfully")
                await asyncio.sleep(86400)  # Засыпаем на 1 день
                
            except Exception as e:
                logger.error(f"Bot crashed: {e}, restarting in 10 seconds...")
                await asyncio.sleep(10)
            finally:
                try:
                    await app.updater.stop()
                    await app.stop()
                    await app.shutdown()
                except:
                    pass
    
    # Запускаем основную петлю
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()