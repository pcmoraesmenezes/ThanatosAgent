import httpx

from src.core.logger import logger
from src.core.settings import settings


TELEGRAM_API_URL = f"https://api.telegram.org/bot{settings.token_telegram}"


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        logger.info(f"Sending message to chat_id: {chat_id}, text: {text}")
        
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("Message sent successfully.")
            
        except httpx.HTTPError as e:
            logger.error(f"Error sending message: {e}")            
        
        