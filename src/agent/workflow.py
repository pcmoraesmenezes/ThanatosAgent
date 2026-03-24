from langgraph.graph import StateGraph, END
from langchain_core.runnables import Runnable
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import ToolNode

from src.agent.state import AgentState
from src.agent.nodes import make_agent_node
from src.agent.tools.tools import AGENT_TOOLS
from src.core.logger import logger


from langchain_core.messages import SystemMessage

async def validator_node(state: AgentState) -> dict:
    messages = state['messages']
    last_msg = messages[-1]

    if 'Error' in last_msg.content:
        return {
            "messages": [SystemMessage(content='Error')]
        }

    return {}



def should_continue(state: AgentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    
    return END


def build_agent_graph(llm: BaseChatModel, checkpointer) -> Runnable:
    
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)
    logger.info("Tools added to LLM.")
    
    workflow = StateGraph(AgentState)

    agent_node = make_agent_node(llm_with_tools)
    tool_node = ToolNode(AGENT_TOOLS) 

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node) 
    workflow.add_node("validator", validator_node)

    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent", 
        should_continue, 
        ["tools", END]
    )
    
    workflow.add_edge("tools", "validator")
    workflow.add_edge("validator", "agent")
    
    return workflow.compile(
        checkpointer=checkpointer
    )