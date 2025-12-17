import uvicorn
from fastapi import FastAPI

import logging


from src.telegram.start_up import lifespan
from src.telegram.webhook import router as telegram_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("main")


app = FastAPI(
    title="Thanatos Agent API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(telegram_router, tags=["Telegram"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ThanatosAgent"}

if __name__ == "__main__":
    logger.info("Starting Server...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True
    )