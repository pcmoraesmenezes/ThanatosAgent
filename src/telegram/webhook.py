from fastapi import APIRouter, Request, HTTPException

from langchain_core.messages import HumanMessage, RemoveMessage

from src.telegram.message import send_message
from src.core.logger import logger


router = APIRouter()


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

        agent_workflow = request.app.state.agent_workflow
        config = {"configurable": {"thread_id": str(chat_id)}}

        if text.strip().lower() == "/clean":
            logger.info(f"/clean comma received: {chat_id}")
            
            current_state = await agent_workflow.aget_state(config)
            
            if current_state and "messages" in current_state.values:
                messages = current_state.values["messages"]
                
                delete_messages = [RemoveMessage(id=m.id) for m in messages if hasattr(m, 'id')]
                
                if delete_messages:
                    await agent_workflow.aupdate_state(config, {"messages": delete_messages})
            
            await send_message(chat_id, "💀 <b>O Abismo observou.</b>\n\nSuas memórias foram consumidas pelo vazio. O ciclo se encerra aqui.\nEstamos sós novamente.")
            return {"status": 'cleaned'}

        initial_state = {"messages": [HumanMessage(content=text)]}
        
        result = await agent_workflow.ainvoke(initial_state, config=config) 
        
        last_message = result["messages"][-1]
        response_message = last_message.content
        
        await send_message(chat_id, response_message)
            
    return {"status": 'ok'}