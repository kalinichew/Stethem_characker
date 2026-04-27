import asyncio
import os
import httpx
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from PyCharacterAI import get_client

# 1. Загрузка настроек
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CAI_TOKEN = os.getenv("CHARACTER_AI_TOKEN")
# Stethem
#CHARACTER_ID = "ePaCGA9413vjoiTiPurKd9nCg4yEGaOrWMx62rD9zvM"
#Tramp
CHARACTER_ID = "xqVv-6WqhweXtKfXfrOAihjn1M3yP6k9bXVBuVGQ-nw"
#DEFAULT_VOICE_ID = "0a6835bc-7d6f-4e74-8352-fc1fc1a5e6be" 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Глобальные переменные для сессии
cai_client = None
cai_chat = None

async def get_cai_info():
    """Инициализация клиента и создание/получение чата"""
    global cai_client, cai_chat
    if not cai_client:
        logger.info("📡 Подключение к Character.AI и создание чата...")
        cai_client = await get_client(token=CAI_TOKEN)
        # Создаем чат один раз при запуске
        chat, _ = await cai_client.chat.create_chat(CHARACTER_ID)
        cai_chat = chat
    return cai_client, cai_chat

async def fetch_voice_url(room_id, turn_id, candidate_id):
    """Метод из твоего cURL для получения аудио"""
    url = "https://neo.character.ai/multimodal/api/v1/memo/replay"
    headers = {
        "authorization": f"Token {CAI_TOKEN}",
        "content-type": "application/json",
        "origin": "https://character.ai",
        "referer": "https://character.ai/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    }
    payload = {
        "roomId": room_id,
        "turnId": turn_id,
        "candidateId": candidate_id,
        "voiceId": DEFAULT_VOICE_ID
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=20.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("replayUrl") or data.get("url")
            else:
                logger.error(f"❌ Ошибка CAI Voice API: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Ошибка запроса голоса: {e}")
    return None

@dp.message(F.text)
async def handle_all_messages(message: types.Message):
    bot_info = await bot.get_me()
    bot_username = f"@{bot_info.username}"
    
    is_private = message.chat.type == "private"
    is_mentioned = bot_username in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id

    if not (is_private or is_mentioned or is_reply_to_bot):
        return

    wants_voice = "🎤" in message.text
    user_input = message.text.replace(bot_username, "").replace("🎤", "").strip()
    
    if not user_input: return

    await bot.send_chat_action(message.chat.id, "record_voice" if wants_voice else "typing")

    try:
        # Получаем инициализированного клиента и чат
        client, chat = await get_cai_info()
        
        # Отправляем сообщение
        answer = await client.chat.send_message(CHARACTER_ID, chat.chat_id, user_input)
        candidate = answer.get_primary_candidate()
        response_text = candidate.text

        if wants_voice:
            # Используем данные из ответа для запроса аудио
            voice_url = await fetch_voice_url(chat.chat_id, answer.turn_id, candidate.candidate_id)

            if voice_url:
                voice_path = f"voice_{message.from_user.id}.mp3"
                async with httpx.AsyncClient() as http_client:
                    audio_resp = await http_client.get(voice_url)
                    with open(voice_path, "wb") as f:
                        f.write(audio_resp.content)
                
                # Отправляем ТОЛЬКО голосовое
                await message.reply_voice(voice=FSInputFile(voice_path))
                os.remove(voice_path)
                return 

        # Если голос не нужен или ссылка не получена — шлем текст
        await message.reply(response_text)

    except Exception as e:
        logger.error(f"💥 Ошибка: {e}")
        await message.answer("Я отдыхаю. Не заёбывай")

async def main():
    logger.info("🚀 Бот Стэтхэм готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
