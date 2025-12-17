from langchain_core.language_models import BaseChatModel

from typing import Callable, Awaitable

import logging

from src.agent.state import AgentState


logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )

logger = logging.getLogger(__name__)

NodeFunction = Callable[[AgentState], Awaitable[dict]]


def make_agent_node(llm: BaseChatModel) -> NodeFunction:
    """
    Factory que cria o nó de execução do agente injetando a dependência do LLM.
    Retorna uma função assíncrona (Closure) que mantém a referência ao LLM.
    """
    async def call_model_node(state: AgentState) -> dict:
        messages = state["messages"]
        
        logger.info(f"Calling LLM with messages: {messages}")
        
        response = await llm.ainvoke(messages)
        
        return {"messages": [response]}
    
    return call_model_node