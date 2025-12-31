from fastapi import FastAPI
import httpx
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_groq import ChatGroq


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

    connection_string = f"postgresql://{settings.pg_user}:{settings.pg_pass}@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
    
    logger.info("Running Database Setup/Migrations...")
    try:
        async with await AsyncConnection.connect(connection_string, autocommit=True) as conn:
            checkpointer_setup = AsyncPostgresSaver(conn)
            await checkpointer_setup.setup()
            logger.info("Database Setup Complete.")
    except Exception as e:
        logger.critical(f"Database Setup Failed: {e}")
    
    async with AsyncConnectionPool(conninfo=connection_string, max_size=20) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        
        try:
            app.state.agent_workflow = build_agent_graph(llm_instance, checkpointer)
            logger.info("Agent Graph built successfully with Postgres Memory.")
        except Exception as e:
            logger.critical(f"Failed to build Agent Graph: {e}")
            raise e

        webhook_url = f"{settings.ngrok_url}/webhook"
        logger.info(f"Setting webhook URL to: {webhook_url}")
    
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"https://api.telegram.org/bot{settings.token_telegram}/setWebhook?url={webhook_url}")
                if response.status_code != 200:
                    logger.error(f"Failed to set webhook: {response.text}")
                else:
                    logger.info("Webhook set successfully.")
        except Exception as e:
            logger.error(f"Network Error setting webhook: {e}")
        
        yield
        
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(f"https://api.telegram.org/bot{settings.token_telegram}/deleteWebhook")
    except Exception:
        pass
    
    logger.info("Shutdown complete.")