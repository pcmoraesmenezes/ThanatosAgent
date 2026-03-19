from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, trim_messages

from typing import Callable, Awaitable

from src.agent.state import AgentState
from src.agent.prompt.prompt import CORE_PROMPT 
from src.core.settings import settings
from src.core.logger import logger

from langchain_core.runnables.config import RunnableConfig

NodeFunction = Callable[[AgentState, RunnableConfig], Awaitable[dict]]


def make_agent_node(llm: BaseChatModel) -> Callable:
    """
    Factory que cria o nó de execução do agente injetando a dependência do LLM.
    Retorna uma função assíncrona (Closure) que mantém a referência ao LLM.
    """
    
    trimmer = trim_messages(
        max_tokens=settings.context_window,
        strategy="last",
        token_counter=llm,
        include_system=True,
        allow_partial=False,
        start_on="human"
    )
    
    async def call_model_node(state: AgentState, config: RunnableConfig) -> dict:
        messages = state["messages"]
        user_id = config.get("configurable", {}).get("thread_id", "unknown")
        
        messages_with_system = [SystemMessage(content=CORE_PROMPT)] + messages
        trimmed_messages = await trimmer.ainvoke(messages_with_system)

        logger.info(f"Calling LLM for User {user_id}. Message count: {len(messages)}. Last role: {messages[-1].type}")
        logger.debug(f"Full payload: {messages}")
        
        response = await llm.ainvoke(trimmed_messages)
        
        usage = response.usage_metadata
        if usage:
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            tot = usage.get("total_tokens", 0)
            logger.info(
                f"LLM Token Usage | User: {user_id} | In: {inp} | Out: {out} | Total: {tot}", 
                input_tokens=inp,
                output_tokens=out,
                total_tokens=tot,
                user_id=user_id,
                cost_event=True
            )

        return {"messages": [response]}
    
    return call_model_node