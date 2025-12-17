import logging
from fastapi import APIRouter, Request, HTTPException
from langchain_core.messages import HumanMessage

from src.telegram.message import send_message

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        logger.error("Failed to parse JSON body")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        logger.info(f"Processing message: {text} | Chat ID: {chat_id}")

        initial_state = {"messages": [HumanMessage(content=text)]}
        
        agent_workflow = request.app.state.agent_workflow
        
        result = await agent_workflow.ainvoke(initial_state) 
        
        last_message = result["messages"][-1]
        response_message = last_message.content
        
        await send_message(chat_id, response_message)
            
    return {"status": 'ok'}