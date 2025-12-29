from fastapi import FastAPI
import httpx
from contextlib import asynccontextmanager

import aiosqlite


def is_alive_patch(self):
    return True

if not hasattr(aiosqlite.Connection, "is_alive"):
    setattr(aiosqlite.Connection, "is_alive", is_alive_patch)


from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.agent.workflow import build_agent_graph
from src.core.settings import settings
from src.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    logger.info("Initializing dependencies...")

    llm_instance = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=settings.groq_api_key,
        temperature=0.7,
        max_retries=2
    )
    logger.info("LLM initialized.")


    async with aiosqlite.connect("ai_memory/agent_memory_checkpoints.db", check_same_thread=False) as conn:
        
        try:
            memory = AsyncSqliteSaver(conn)
            await memory.setup()

            app.state.agent_workflow = build_agent_graph(llm_instance, memory)
            logger.info("Agent Graph built successfully with Async Memory.")
            
        except Exception as e:
            logger.critical(f"Failed to build Agent Graph: {e}")
            raise e

        logger.info("Checkpointer initialized.")
        
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
