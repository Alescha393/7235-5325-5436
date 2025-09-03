import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция для пересылки сообщений в канал"""
    try:
        # Используем message_id для пересылки, а не текст сообщения :cite[1]
        await update.message.forward(chat_id=config.CHANNEL_ID)
        logger.info(f"Сообщение переслано в канал {config.CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Ошибка при пересылке сообщения: {e}")

async def forward_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция для пересылки документов в канал"""
    try:
        document = update.message.document
        await context.bot.send_document(
            chat_id=config.CHANNEL_ID,
            document=document.file_id,
            caption=update.message.caption
        )
        logger.info(f"Документ переслан в канал {config.CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Ошибка при пересылке документа: {e}")

async def forward_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция для пересылки фото в канал"""
    try:
        photo = update.message.photo[-1]  # Берем самую большую версию фото
        await context.bot.send_photo(
            chat_id=config.CHANNEL_ID,
            photo=photo.file_id,
            caption=update.message.caption
        )
        logger.info(f"Фото переслано в канал {config.CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Ошибка при пересылке фото: {e}")

async def forward_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция для пересылки видео в канал"""
    try:
        video = update.message.video
        await context.bot.send_video(
            chat_id=config.CHANNEL_ID,
            video=video.file_id,
            caption=update.message.caption
        )
        logger.info(f"Видео переслано в канал {config.CHANNEL_ID}")
    except Exception as e:
        logger.error(f"Ошибка при пересылке видео: {e}")

def main():
    # Создаем приложение и передаем токен бота
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Добавляем обработчики для разных типов сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))
    application.add_handler(MessageHandler(filters.DOCUMENT, forward_document))
    application.add_handler(MessageHandler(filters.PHOTO, forward_photo))
    application.add_handler(MessageHandler(filters.VIDEO, forward_video))

    # Запускаем бота
    application.run_polling()
    logger.info("Бот запущен и готов к работе")

if __name__ == "__main__":
    main()
