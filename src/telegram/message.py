import httpx

import logging

from src.core.settings import settings


TELEGRAM_API_URL = f"https://api.telegram.org/bot{settings.token_telegram}"

logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )

logger = logging.getLogger(__name__)



async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        logger.info(f"Sending message to chat_id: {chat_id}, text: {text}")
        
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        await client.post(url, json=payload)
        
        