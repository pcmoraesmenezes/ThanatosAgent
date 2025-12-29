from src.agent.tools.db_tools import check_local_database, save_product_memory
from src.agent.tools.search_tools import search_web_products


AGENT_TOOLS = [check_local_database, search_web_products, save_product_memory]