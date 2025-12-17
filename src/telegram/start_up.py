from fastapi import FastAPI
import httpx
from contextlib import asynccontextmanager

import logging

from langchain_groq import ChatGroq

from src.agent.workflow import build_agent_graph
from src.core.settings import settings

logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    logger.info("Initializing dependencies...")

    llm_instance = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key,
        temperature=0.7,
        max_retries=2
    )
    logger.info("LLM initialized.")

    try:
        app.state.agent_workflow = build_agent_graph(llm_instance)
        logger.info("Agent Graph built successfully.")
    except Exception as e:
        logger.critical(f"Failed to build Agent Graph: {e}")
        raise e

    webhook_url = f"{settings.ngrok_url}/webhook"
    logger.info(f"Setting webhook URL to: {webhook_url}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.telegram.org/bot{settings.token_telegram}/setWebhook?url={webhook_url}")
        if response.status_code != 200:
            logger.error(f"Failed to set webhook: {response.text}")
    
    yield
    
    async with httpx.AsyncClient() as client:
        await client.get(f"https://api.telegram.org/bot{settings.token_telegram}/deleteWebhook")
    logger.info("Shutdown complete.")
