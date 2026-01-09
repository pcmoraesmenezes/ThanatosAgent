from src.agent.tools.db_tools import check_local_database, save_product_memory
from src.agent.tools.search_tools import search_web_products
from src.agent.tools.price_tools import check_price_from_url
from src.agent.tools.alert_tools import create_price_alert


AGENT_TOOLS = [check_local_database, search_web_products, save_product_memory, check_price_from_url, create_price_alert]