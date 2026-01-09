from langchain_core.tools import tool

from src.services.catalog_service import CatalogService
from src.repository.alert_repository import AlertRepository
from src.core.logger import logger


catalog_service = CatalogService()
alert_repo = AlertRepository()

@tool
async def create_price_alert(url: str, target_price: float, chat_id: int) -> str:
    """
    Creates a price alert (Watchdog) for a specific product URL.
    
    ARGS:
    - url: The product URL.
    - target_price: The price threshold to trigger the alert.
    - chat_id: The user's telegram ID (Context).

    RETURNS:
    - Success or error message.
    """
    try:
        product_id = await catalog_service.register_product(
            url=url,
            title="Tracking Request", 
            price=0, 
            description="User Watchdog Request"
        )
        
        alert_id = await alert_repo.create_alert(product_id, chat_id, target_price)
        
        return f"Vigilância iniciada. Alerta ID {alert_id} definido para R$ {target_price:.2f}."
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        return "Erro ao criar alerta. Verifique a URL."