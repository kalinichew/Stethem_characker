import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from PyCharacterAI import get_client

# Загрузка переменных
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHARACTER_AI_TOKEN = os.getenv("CHARACTER_AI_TOKEN")
CHARACTER_ID = "ePaCGA9413vjoiTiPurKd9nCg4yEGaOrWMx62rD9zvM"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Глобальные переменные для клиента
cai_client = None
cai_chat = None

async def get_cai_info():
    """Функция инициализации клиента и чата Character.AI"""
    global cai_client, cai_chat
    if not cai_client:
        logger.info("📡 Инициализация Character.AI клиента...")
        cai_client = await get_client(token=CHARACTER_AI_TOKEN)
        # Создаем или продолжаем чат
        chat, _ = await cai_client.chat.create_chat(CHARACTER_ID)
        cai_chat = chat
    return cai_client, cai_chat

@dp.message(F.text)
async def handle_all_messages(message: types.Message):
    # Получаем актуальную информацию о боте
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    # Условия для ответа
    is_private = message.chat.type == "private"
    is_mentioned = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id

    # Если это не личка и не обращение к боту — игнорируем
    if not (is_private or is_mentioned or is_reply_to_bot):
        return

    # Очищаем текст сообщения от тега бота
    user_input = message.text.replace(bot_username, "").strip()
    
    if not user_input:
        return

    # Показываем статус "печатает"
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Вызываем функцию инициализации (ВАЖНО: имя должно совпадать!)
        client, chat = await get_cai_info()
        
        # Отправляем сообщение в Character.AI
        answer = await client.chat.send_message(CHARACTER_ID, chat.chat_id, user_input)
        response_text = answer.get_primary_candidate().text
        
        # Ответ пользователю
        await message.reply(response_text)
        
    except Exception as e:
        logger.error(f"Ошибка при работе с CAI: {e}")
        await message.answer("⚠️ Джейсон занят на съемках (ошибка связи). Попробуй позже.")

async def main():
    if not TELEGRAM_TOKEN or not CHARACTER_AI_TOKEN:
        logger.error("Токены не найдены в .env! Проверьте файл.")
        return

    logger.info("🚀 Бот Джейсон Стэтхэм запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")