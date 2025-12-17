from langgraph.graph import StateGraph, END
from langchain_core.runnables import Runnable
from langchain_core.language_models import BaseChatModel


import logging

from src.agent.state import AgentState
from src.agent.nodes import make_agent_node


logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )

logger = logging.getLogger(__name__)



def build_agent_graph(llm: BaseChatModel) -> Runnable:
    workflow = StateGraph(AgentState)

    agent_node = make_agent_node(llm)

    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    return workflow.compile()